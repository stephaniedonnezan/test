"""Build Linear issue title updates for Cursor research status automations."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_DIRECT_STATUS_EVENTS = {
    "status changed",
    "status change",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
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
    "workflowstate",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update action when an issue enters To Research.

    The function is intentionally side-effect free so the caller can decide how
    to execute the returned action against Linear.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    if _normalize_status(_find_new_status(event)) != TARGET_STATUS:
        return None

    issue_id = _first_text_value(event, ("issueId", "issue_id", "id", "identifier", "key"))
    title = _first_text_value(event, ("title",))
    if issue_id is None or title is None:
        return None

    trimmed_title = title.strip()
    if not trimmed_title:
        return None
    if trimmed_title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {trimmed_title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    event_names = {
        _normalize_event_name(value)
        for value in _collect_values(event, ("trigger", "action", "type", "webhookType", "eventType"))
    }
    event_names.discard("")

    if event_names & _DIRECT_STATUS_EVENTS:
        return True
    if any("status" in name and "changed" in name for name in event_names):
        return True

    if event_names & _GENERIC_UPDATE_EVENTS:
        return _has_status_change_metadata(event)

    return False


def _has_status_change_metadata(event: Mapping[str, Any]) -> bool:
    for value in _collect_values(event, ("updatedFields", "changedFields")):
        if _contains_status_field_name(value):
            return True

    for mapping in _walk_mappings(event):
        changes = mapping.get("changes")
        if isinstance(changes, Mapping) and any(_is_status_field_name(key) for key in changes):
            return True

    return False


def _find_new_status(event: Mapping[str, Any]) -> Any:
    explicit_status_keys = (
        "newStatus",
        "new_status",
        "newStatusName",
        "new_status_name",
        "toStatus",
        "to_status",
        "newState",
        "new_state",
        "toState",
        "to_state",
        "newWorkflowState",
        "new_workflow_state",
    )
    for value in _collect_values(event, explicit_status_keys):
        status = _status_name(value)
        if status is not None:
            return status

    for status in _statuses_from_changes(event):
        return status

    for value in _collect_values(event, ("status", "state", "workflowState", "workflow_state")):
        status = _status_name(value)
        if status is not None:
            return status

    return None


def _statuses_from_changes(event: Mapping[str, Any]) -> Iterable[Any]:
    for mapping in _walk_mappings(event):
        changes = mapping.get("changes")
        if not isinstance(changes, Mapping):
            continue

        for key, value in changes.items():
            if not _is_status_field_name(key):
                continue

            if isinstance(value, Mapping):
                for value_key in ("to", "new", "newValue", "new_value", "after", "current"):
                    status = _status_name(value.get(value_key))
                    if status is not None:
                        yield status
                        break
            else:
                status = _status_name(value)
                if status is not None:
                    yield status


def _first_text_value(event: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for value in _collect_values(event, keys):
        text = _text_value(value)
        if text:
            return text
    return None


def _collect_values(event: Mapping[str, Any], keys: tuple[str, ...]) -> Iterable[Any]:
    lowered_keys = {key.lower() for key in keys}
    for mapping in _walk_mappings(event):
        for key, value in mapping.items():
            if isinstance(key, str) and key.lower() in lowered_keys:
                yield value


def _walk_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for nested in value.values():
            yield from _walk_mappings(nested)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_mappings(item)


def _contains_status_field_name(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field_name(value)
    if isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray, Mapping)):
        return any(_contains_status_field_name(item) for item in value)
    return False


def _is_status_field_name(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    return _normalize_event_name(value) in _STATUS_FIELD_NAMES


def _status_name(value: Any) -> str | None:
    text = _text_value(value)
    if text is not None:
        return text

    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            text = _text_value(value.get(key))
            if text is not None:
                return text

    return None


def _text_value(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped if stripped else None
    return None


def _normalize_status(value: Any) -> str:
    text = _status_name(value)
    if text is None:
        return ""
    return _normalize_event_name(text)


def _normalize_event_name(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    normalized = re.sub(r"[^a-zA-Z0-9]+", " ", spaced).strip().lower()
    return re.sub(r"\s+", " ", normalized)


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(build_issue_title_update(event), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
