"""Build Linear issue title updates for Cursor research automation."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_DIRECT_STATUS_CHANGE_TRIGGERS = {
    "status change",
    "status changed",
    "state change",
    "state changed",
    "workflow state change",
    "workflow state changed",
}
_GENERIC_UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}
_TRIGGER_KEYS = ("trigger", "action", "type", "webhookType", "webhook_type", "event")
_EXPLICIT_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "toStatus",
    "to_status",
    "statusName",
    "status_name",
    "stateName",
    "state_name",
    "workflowStateName",
    "workflow_state_name",
)
_STATUS_KEYS = (
    "status",
    "state",
    "workflowState",
    "workflow_state",
)
_STATUS_MARKER_KEYS = {
    "status",
    "statusId",
    "status_id",
    "state",
    "stateId",
    "state_id",
    "workflowState",
    "workflow_state",
    "workflowStateId",
    "workflow_state_id",
}
_TITLE_KEYS = ("title", "issueTitle", "issue_title")
_PREFERRED_ID_KEYS = ("issueId", "issue_id", "identifier", "key")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue enters research.

    The Cursor automation trigger can provide a flat ``triggerContext`` payload,
    while Linear webhooks often nest issue fields under ``data.issue``. This
    function accepts both shapes and ignores unrelated events.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = list(_collect_contexts(event))
    if not _is_status_change_event(contexts):
        return None

    status = _extract_new_status(contexts)
    if _normalize_text(status) != TARGET_STATUS:
        return None

    issue_contexts = list(_collect_issue_contexts(event))
    issue_id = _extract_issue_id(issue_contexts)
    title = _extract_title(issue_contexts)
    if not issue_id or not title:
        return None

    title = title.strip()
    if not title or title.casefold().startswith(PREFIX.casefold()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _collect_contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield shallow nested mappings that may contain trigger or status data."""

    seen: set[int] = set()
    stack: list[Any] = [event]
    while stack:
        value = stack.pop(0)
        if not isinstance(value, Mapping):
            continue

        value_id = id(value)
        if value_id in seen:
            continue
        seen.add(value_id)
        yield value

        for key in (
            "triggerContext",
            "data",
            "issue",
            "state",
            "status",
            "workflowState",
            "workflow_state",
            "changes",
            "updatedFrom",
            "updated_from",
        ):
            nested = value.get(key)
            if isinstance(nested, Mapping):
                stack.append(nested)


def _collect_issue_contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield mappings that are likely to describe the Linear issue itself."""

    seen: set[int] = set()

    def emit(value: Any) -> Iterable[Mapping[str, Any]]:
        if isinstance(value, Mapping) and id(value) not in seen:
            seen.add(id(value))
            yield value

    yield from emit(event.get("triggerContext"))

    data = event.get("data")
    if isinstance(data, Mapping):
        yield from emit(data.get("issue"))
        if any(key in data for key in _TITLE_KEYS):
            yield from emit(data)

    yield from emit(event.get("issue"))

    if any(key in event for key in _TITLE_KEYS):
        yield from emit(event)

    for context in _collect_contexts(event):
        if any(key in context for key in _TITLE_KEYS):
            yield from emit(context)


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    trigger_values = [
        _normalize_text(context[key])
        for context in contexts
        for key in _TRIGGER_KEYS
        if key in context
    ]
    trigger_values = [value for value in trigger_values if value]

    if any(_is_direct_status_trigger(value) for value in trigger_values):
        return True

    has_status_marker = _has_status_update_marker(contexts)
    if any(value in _GENERIC_UPDATE_TRIGGERS for value in trigger_values):
        return has_status_marker

    return has_status_marker and not trigger_values


def _is_direct_status_trigger(value: str) -> bool:
    compact = value.replace(" ", "")
    return value in _DIRECT_STATUS_CHANGE_TRIGGERS or compact in {
        "statuschanged",
        "statuschange",
        "statechanged",
        "statechange",
        "workflowstatechanged",
        "workflowstatechange",
    }


def _has_status_update_marker(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        if any(key in context for key in _EXPLICIT_STATUS_KEYS):
            return True

        updated_fields = context.get("updatedFields") or context.get("updated_fields")
        if _contains_status_marker(updated_fields):
            return True

        for key in ("changes", "updatedFrom", "updated_from"):
            if _mapping_has_status_key(context.get(key)):
                return True

    return False


def _extract_new_status(contexts: list[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        for key in _EXPLICIT_STATUS_KEYS:
            value = _status_value(context.get(key))
            if value:
                return value

    for context in contexts:
        for key in ("changes", "updatedFrom", "updated_from"):
            value = _status_from_change_map(context.get(key))
            if value:
                return value

    for context in contexts:
        for key in _STATUS_KEYS:
            value = _status_value(context.get(key))
            if value:
                return value

    return None


def _status_from_change_map(value: Any) -> str | None:
    if not isinstance(value, Mapping):
        return None

    for key, nested in value.items():
        if not _is_status_marker_key(key):
            continue
        if isinstance(nested, Mapping):
            for to_key in ("to", "toValue", "to_value", "new", "newValue", "new_value", "name"):
                status = _status_value(nested.get(to_key))
                if status:
                    return status
        else:
            status = _status_value(nested)
            if status:
                return status
    return None


def _mapping_has_status_key(value: Any) -> bool:
    return isinstance(value, Mapping) and any(_is_status_marker_key(key) for key in value)


def _contains_status_marker(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_marker_key(value)
    if isinstance(value, Mapping):
        return any(_is_status_marker_key(key) or _contains_status_marker(nested) for key, nested in value.items())
    if isinstance(value, Iterable):
        return any(_contains_status_marker(item) for item in value)
    return False


def _is_status_marker_key(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    normalized = _normalize_text(value)
    compact = normalized.replace(" ", "")
    normalized_markers = {_normalize_text(key) for key in _STATUS_MARKER_KEYS}
    compact_markers = {marker.replace(" ", "") for marker in normalized_markers}
    return normalized in normalized_markers or compact in compact_markers


def _status_value(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, Mapping):
        for key in ("name", "title", "status", "state"):
            status = _status_value(value.get(key))
            if status:
                return status
    return None


def _extract_issue_id(contexts: list[Mapping[str, Any]]) -> str | None:
    for key in _PREFERRED_ID_KEYS:
        for context in contexts:
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

    for context in contexts:
        value = context.get("id")
        if isinstance(value, str) and value.strip():
            return value.strip()

    return None


def _extract_title(contexts: list[Mapping[str, Any]]) -> str | None:
    for key in _TITLE_KEYS:
        for context in contexts:
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().casefold()


def main() -> int:
    event = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(event), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
