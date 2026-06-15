"""Build Linear issue title updates for issues moved to research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping, Sequence
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_DIRECT_STATUS_CHANGE_EVENTS = {
    "status changed",
    "state changed",
    "workflow state changed",
}
_GENERIC_UPDATE_EVENTS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}
_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflow state",
    "workflow status",
}
_TRIGGER_KEYS = ("trigger", "webhookType", "action", "type", "event", "eventType")
_EXPLICIT_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "toStatus",
    "to_status",
    "targetStatus",
    "target_status",
    "newState",
    "new_state",
)
_CURRENT_STATUS_KEYS = ("status", "state", "workflowState", "workflow_state")
_UPDATED_FIELD_KEYS = (
    "updatedFields",
    "changedFields",
    "changes",
    "changed",
    "updatedFrom",
    "previousValues",
)
_ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "key", "id")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to research.

    The automation receives slightly different shapes depending on whether the
    payload comes from Cursor's trigger context or directly from Linear. This
    function accepts both flat and nested payloads and returns ``None`` for
    unrelated events.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _candidate_contexts(event)
    if not _is_status_change_event(contexts):
        return None

    status = _extract_status(contexts)
    if _normalize(status) != TARGET_STATUS:
        return None

    issue_id = _extract_issue_id(contexts)
    title = _extract_title(contexts)
    if not issue_id or not title:
        return None

    title = title.strip()
    if not title or _already_prefixed(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _candidate_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and not any(value is context for context in contexts):
            contexts.append(value)

    add(event)
    add(event.get("triggerContext"))
    add(event.get("data"))
    add(event.get("issue"))

    data = event.get("data")
    if isinstance(data, Mapping):
        add(data.get("issue"))

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        add(trigger_context.get("issue"))
        nested_data = trigger_context.get("data")
        add(nested_data)
        if isinstance(nested_data, Mapping):
            add(nested_data.get("issue"))

    return contexts


def _is_status_change_event(contexts: Sequence[Mapping[str, Any]]) -> bool:
    trigger_values = [
        _normalize(context[key])
        for context in contexts
        for key in _TRIGGER_KEYS
        if key in context
    ]

    if any(value in _DIRECT_STATUS_CHANGE_EVENTS for value in trigger_values):
        return True

    if any(value in _GENERIC_UPDATE_EVENTS for value in trigger_values):
        return _has_status_change_metadata(contexts)

    return _has_explicit_status(contexts) and _has_status_change_metadata(contexts)


def _has_status_change_metadata(contexts: Sequence[Mapping[str, Any]]) -> bool:
    if _has_explicit_status(contexts):
        return True

    return any(
        _contains_status_field(context.get(key))
        for context in contexts
        for key in _UPDATED_FIELD_KEYS
        if key in context
    )


def _has_explicit_status(contexts: Sequence[Mapping[str, Any]]) -> bool:
    return any(key in context for context in contexts for key in _EXPLICIT_STATUS_KEYS)


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(
            _is_status_field_name(key) or _contains_status_field(nested)
            for key, nested in value.items()
        )

    if isinstance(value, str):
        return _is_status_field_name(value)

    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        return any(_contains_status_field(item) for item in value)

    return False


def _extract_status(contexts: Sequence[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        for key in _EXPLICIT_STATUS_KEYS:
            value = _string_value(context.get(key))
            if value:
                return value

    for context in contexts:
        for key in _CURRENT_STATUS_KEYS:
            value = _string_value(context.get(key))
            if value:
                return value

    return None


def _extract_issue_id(contexts: Sequence[Mapping[str, Any]]) -> str | None:
    for key in _ISSUE_ID_KEYS:
        for context in contexts:
            value = _string_value(context.get(key))
            if value:
                return value.strip()

    return None


def _extract_title(contexts: Sequence[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        value = _string_value(context.get("title"))
        if value:
            return value

    return None


def _string_value(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip()

    if isinstance(value, Mapping):
        for key in ("name", "title"):
            nested = value.get(key)
            if isinstance(nested, str) and nested.strip():
                return nested.strip()

    return None


def _already_prefixed(title: str) -> bool:
    return re.match(rf"^\s*{re.escape(PREFIX)}\b", title, flags=re.IGNORECASE) is not None


def _is_status_field_name(value: Any) -> bool:
    return _normalize(value) in _STATUS_FIELD_NAMES


def _normalize(value: Any) -> str:
    if value is None:
        return ""

    text = str(value).strip()
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def main() -> int:
    event = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(event), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
