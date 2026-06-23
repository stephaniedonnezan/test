"""Build Linear issue title updates for Cursor research status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_EVENT_MARKER_KEYS = {
    "action",
    "event",
    "event_type",
    "eventtype",
    "trigger",
    "type",
    "webhook_type",
    "webhooktype",
}
_STATUS_FIELD_NAMES = {"status", "state", "workflow state", "workflow status"}
_UPDATED_FIELD_KEYS = {
    "changed_attributes",
    "changedattributes",
    "changed_fields",
    "changedfields",
    "updated_fields",
    "updatedfields",
    "updated_properties",
    "updatedproperties",
}
_CHANGE_CONTAINER_KEYS = {
    "changes",
    "changed",
    "status_change",
    "statuschange",
    "state_change",
    "statechange",
}
_EXPLICIT_STATUS_KEYS = {
    "new_status",
    "newstatus",
    "status_name",
    "statusname",
    "state_name",
    "statename",
    "to_status",
    "tostatus",
    "workflow_state_name",
    "workflowstatename",
}
_CURRENT_STATUS_KEYS = {"status", "state", "workflow_state", "workflowstate"}
_ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "key", "id")
_TITLE_KEYS = ("title", "issueTitle", "issue_title")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return the title update action for a Linear issue entering research.

    The function is intentionally side-effect free so the automation runner can
    decide how to apply the returned action.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    new_status = _extract_new_status(event)
    if _normalize_phrase(new_status) != TARGET_STATUS:
        return None

    issue_id = _extract_first_text(event, _ISSUE_ID_KEYS)
    title = _extract_first_text(event, _TITLE_KEYS)
    if not issue_id or not title:
        return None

    title = title.strip()
    if not title or title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    markers = {
        _normalize_phrase(value)
        for mapping in _walk_mappings(event)
        for key, value in mapping.items()
        if _normalize_key(key) in _EVENT_MARKER_KEYS
    }

    if any(_is_direct_status_change_marker(marker) for marker in markers):
        return True

    return any(_is_generic_issue_update_marker(marker) for marker in markers) and _has_status_change_marker(event)


def _is_direct_status_change_marker(marker: str) -> bool:
    if not marker:
        return False
    return "status" in marker and ("change" in marker or "changed" in marker or "update" in marker)


def _is_generic_issue_update_marker(marker: str) -> bool:
    return marker in {"update", "updated", "issue update", "issue updated", "updated issue"}


def _has_status_change_marker(event: Mapping[str, Any]) -> bool:
    for mapping in _walk_mappings(event):
        for key, value in mapping.items():
            normalized_key = _normalize_key(key)
            if normalized_key in _UPDATED_FIELD_KEYS and _contains_status_field_name(value):
                return True
            if normalized_key in _CHANGE_CONTAINER_KEYS and _change_container_new_status(value) is not None:
                return True
            if normalized_key in _EXPLICIT_STATUS_KEYS:
                return True
    return False


def _extract_new_status(event: Mapping[str, Any]) -> Any:
    for mapping in _walk_mappings(event):
        for key, value in mapping.items():
            if _normalize_key(key) in _EXPLICIT_STATUS_KEYS:
                return _status_text(value)

    for mapping in _walk_mappings(event):
        for key, value in mapping.items():
            if _normalize_key(key) in _CHANGE_CONTAINER_KEYS:
                changed_status = _change_container_new_status(value)
                if changed_status is not None:
                    return changed_status

    for mapping in _context_mappings(event):
        for key in _CURRENT_STATUS_KEYS:
            for actual_key, value in mapping.items():
                if _normalize_key(actual_key) == key:
                    return _status_text(value)

    return None


def _change_container_new_status(value: Any) -> Any:
    if isinstance(value, Mapping):
        for key, change in value.items():
            if _is_status_field_name(key):
                return _extract_change_new_value(change)

        if _contains_status_field_name(value.get("field") or value.get("name") or value.get("property")):
            return _extract_change_new_value(value)

    if isinstance(value, Iterable) and not isinstance(value, (str, bytes, bytearray, Mapping)):
        for item in value:
            changed_status = _change_container_new_status(item)
            if changed_status is not None:
                return changed_status

    return None


def _extract_change_new_value(change: Any) -> Any:
    if isinstance(change, Mapping):
        for key in ("to", "new", "after", "current", "value", "newValue", "new_value"):
            if key in change:
                return _status_text(change[key])
        return None
    return _status_text(change)


def _contains_status_field_name(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field_name(value)
    if isinstance(value, Mapping):
        return any(_contains_status_field_name(item) for pair in value.items() for item in pair)
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes, bytearray)):
        return any(_contains_status_field_name(item) for item in value)
    return False


def _is_status_field_name(value: Any) -> bool:
    return _normalize_phrase(value) in _STATUS_FIELD_NAMES


def _extract_first_text(event: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    normalized_keys = {_normalize_key(key) for key in keys}
    for mapping in _context_mappings(event):
        for key, value in mapping.items():
            if _normalize_key(key) in normalized_keys:
                text = _text(value)
                if text and text.strip():
                    return text
    return None


def _context_mappings(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    paths = (
        ("triggerContext",),
        ("automation_trigger_info", "triggerContext"),
        ("automationTriggerInfo", "triggerContext"),
        ("trigger_context",),
        ("data", "issue"),
        ("issue",),
        ("data",),
        (),
    )

    contexts: list[Mapping[str, Any]] = []
    seen: set[int] = set()
    for path in paths:
        current: Any = event
        for part in path:
            if not isinstance(current, Mapping):
                current = None
                break
            current = current.get(part)
        if isinstance(current, Mapping) and id(current) not in seen:
            contexts.append(current)
            seen.add(id(current))
    return contexts


def _walk_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for child in value.values():
            yield from _walk_mappings(child)
    elif isinstance(value, Iterable) and not isinstance(value, (str, bytes, bytearray)):
        for child in value:
            yield from _walk_mappings(child)


def _status_text(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("name", "title", "label", "status", "state"):
            text = _text(value.get(key))
            if text:
                return text
        return None
    return _text(value)


def _text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        return str(value)
    return None


def _normalize_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", _normalize_phrase(value))


def _normalize_phrase(value: Any) -> str:
    text = _status_text(value)
    if not text:
        return ""
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    return " ".join(re.sub(r"[^a-zA-Z0-9]+", " ", spaced).lower().split())


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON input: {exc}", file=sys.stderr)
        return 2

    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
