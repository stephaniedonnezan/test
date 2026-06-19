"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflowstate",
    "workflowstatus",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title-update action when a Linear issue moves to research."""
    if not isinstance(event, Mapping):
        return None

    payload = _flatten_payload(event)
    if not _is_status_change_event(payload):
        return None

    new_status = _extract_status(payload)
    if _normalize_label(new_status) != TARGET_STATUS:
        return None

    issue_id = _first_text(payload, "issueId", "issue_id", "identifier", "key", "id")
    title = _first_text(payload, "title")
    if not issue_id or not title:
        return None

    if _has_cursor_researching_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _flatten_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common wrapper objects while keeping outer webhook metadata."""
    flattened: dict[str, Any] = {}
    for key in ("issue", "data", "triggerContext"):
        nested = event.get(key)
        if isinstance(nested, Mapping):
            flattened.update(_flatten_payload(nested))

    flattened.update(event)
    return flattened


def _is_status_change_event(payload: Mapping[str, Any]) -> bool:
    trigger_values = [
        payload.get(key)
        for key in ("trigger", "webhookType", "action", "type")
        if payload.get(key) is not None
    ]

    for value in trigger_values:
        normalized = _normalize_label(value)
        if normalized in {
            "status changed",
            "status change",
            "state changed",
            "workflow state changed",
        }:
            return True

    if any(_normalize_label(value) in {"issue updated", "updated issue", "update"} for value in trigger_values):
        return _updated_fields_include_status(payload)

    return _updated_fields_include_status(payload)


def _updated_fields_include_status(payload: Mapping[str, Any]) -> bool:
    updated_fields = payload.get("updatedFields") or payload.get("updated_fields")
    if _field_list_includes_status(updated_fields):
        return True

    changes = payload.get("changes") or payload.get("changedFields") or payload.get("changed_fields")
    if isinstance(changes, Mapping):
        return any(_normalize_key(key) in STATUS_FIELD_NAMES for key in changes)

    return _field_list_includes_status(changes)


def _field_list_includes_status(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_key(value) in STATUS_FIELD_NAMES

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return any(_normalize_key(item) in STATUS_FIELD_NAMES for item in value)

    return False


def _extract_status(payload: Mapping[str, Any]) -> str | None:
    for key in ("newStatus", "new_status", "statusName", "status_name", "newState", "new_state"):
        value = _text_or_nested_name(payload.get(key))
        if value:
            return value

    changes = payload.get("changes") or payload.get("changedFields") or payload.get("changed_fields")
    if isinstance(changes, Mapping):
        for key in ("status", "state", "workflowState", "workflow_status"):
            value = _changed_field_value(changes.get(key))
            if value:
                return value

    for key in ("status", "state", "workflowState", "workflow_status"):
        value = _text_or_nested_name(payload.get(key))
        if value:
            return value

    return None


def _changed_field_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("to", "new", "after", "name"):
            text = _text_or_nested_name(value.get(key))
            if text:
                return text
    return _text_or_nested_name(value)


def _first_text(payload: Mapping[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str):
            stripped = value.strip()
            if stripped:
                return stripped
    return None


def _text_or_nested_name(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None

    if isinstance(value, Mapping):
        for key in ("name", "title"):
            text = _text_or_nested_name(value.get(key))
            if text:
                return text

    return None


def _has_cursor_researching_prefix(title: str) -> bool:
    return _normalize_label(title).startswith(_normalize_label(PREFIX))


def _normalize_label(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return re.sub(r"[^a-z0-9]+", " ", spaced.casefold()).strip()


def _normalize_key(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def main() -> int:
    """Read a JSON event from stdin and print the computed action, if any."""
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action, indent=2, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
