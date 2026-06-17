"""Build Linear issue title updates for research status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflowstate",
    "workflow_state",
    "workflow state",
}
_DIRECT_STATUS_CHANGE_EVENTS = {
    "status changed",
    "status change",
    "status updated",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
}
_GENERIC_ISSUE_UPDATE_EVENTS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}
_EXPLICIT_NEW_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newStatusName",
    "new_status_name",
    "statusName",
    "status_name",
    "stateName",
    "state_name",
    "workflowStateName",
    "workflow_state_name",
    "newState",
    "new_state",
)
_CURRENT_STATUS_KEYS = ("status", "state", "workflowState", "workflow_state")
_TRIGGER_KEYS = ("trigger", "webhookType", "eventType", "type", "action", "event")
_ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "key", "id")


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to To Research.

    The function is side-effect free so automation runners can decide how to
    dispatch the returned update to Linear.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = list(_contexts(event))
    if not _is_status_change_event(contexts):
        return None

    new_status = _find_new_status(contexts)
    if _normalize_text(new_status) != TARGET_STATUS:
        return None

    issue_id = _find_text(contexts, _ISSUE_ID_KEYS)
    title = _find_text(contexts, ("title",))
    if not issue_id or not title:
        return None

    clean_title = title.strip()
    if _has_prefix(clean_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {clean_title}",
    }


def _contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely metadata/issue dictionaries from flat and nested payloads."""

    seen: set[int] = set()

    def visit(value: Any) -> Iterable[Mapping[str, Any]]:
        if not isinstance(value, Mapping):
            return

        marker = id(value)
        if marker in seen:
            return
        seen.add(marker)
        yield value

        for key in ("triggerContext", "data", "issue"):
            child = value.get(key)
            if isinstance(child, Mapping):
                yield from visit(child)

    yield from visit(event)


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    trigger_values = [
        _normalize_text(context.get(key))
        for context in contexts
        for key in _TRIGGER_KEYS
        if context.get(key) is not None
    ]

    if any(value in _DIRECT_STATUS_CHANGE_EVENTS for value in trigger_values):
        return True

    if any(value in _GENERIC_ISSUE_UPDATE_EVENTS for value in trigger_values):
        return _has_status_changed_field(contexts)

    return False


def _has_status_changed_field(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "changedFields", "changes", "updatedFrom"):
            value = context.get(key)
            if _contains_status_field(value):
                return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_field_name(value) in _STATUS_FIELD_NAMES

    if isinstance(value, Mapping):
        for key, child in value.items():
            if _normalize_field_name(key) in _STATUS_FIELD_NAMES:
                return True
            if _contains_status_field(child):
                return True
        return False

    if isinstance(value, Iterable):
        return any(_contains_status_field(item) for item in value)

    return False


def _find_new_status(contexts: list[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        status = _find_text([context], _EXPLICIT_NEW_STATUS_KEYS)
        if status:
            return status

    for context in contexts:
        for key in ("changes", "updatedFields", "changedFields"):
            status = _status_from_change_metadata(context.get(key))
            if status:
                return status

    for context in contexts:
        status = _find_text([context], _CURRENT_STATUS_KEYS)
        if status:
            return status

    return None


def _status_from_change_metadata(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if _normalize_field_name(key) in _STATUS_FIELD_NAMES:
                status = _extract_text(
                    child,
                    (
                        "to",
                        "new",
                        "after",
                        "value",
                        "newValue",
                        "new_value",
                        "name",
                    ),
                )
                if status:
                    return status

            status = _status_from_change_metadata(child)
            if status:
                return status

    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        for item in value:
            if isinstance(item, Mapping):
                field = _find_text([item], ("field", "name", "key"))
                if field and _normalize_field_name(field) in _STATUS_FIELD_NAMES:
                    status = _extract_text(
                        item,
                        ("to", "new", "after", "value", "newValue", "new_value"),
                    )
                    if status:
                        return status

            status = _status_from_change_metadata(item)
            if status:
                return status

    return None


def _find_text(contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for context in contexts:
        for key in keys:
            if key in context:
                text = _extract_text(context[key])
                if text:
                    return text

    return None


def _extract_text(value: Any, preferred_keys: Iterable[str] = ("name",)) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None

    if isinstance(value, (int, float)):
        return str(value)

    if isinstance(value, Mapping):
        for key in preferred_keys:
            if key in value:
                text = _extract_text(value[key], preferred_keys)
                if text:
                    return text

    return None


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def _normalize_field_name(value: Any) -> str:
    normalized = _normalize_text(value)
    return normalized.replace(" ", "")


def _normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    normalized = re.sub(r"[^a-zA-Z0-9]+", " ", spaced).strip().lower()
    return re.sub(r"\s+", " ", normalized)


def main() -> int:
    event = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(event), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
