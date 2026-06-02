"""Build Linear issue title updates for research-status automations."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
TITLE_SEPARATOR = ": "
STATUS_FIELDS = {"status", "state", "state id", "workflow state", "workflowstate"}
STATUS_CHANGE_EVENTS = {
    "status change",
    "status changed",
    "status update",
    "status updated",
    "state change",
    "state changed",
    "workflow state change",
    "workflow state changed",
}
ISSUE_UPDATE_EVENTS = {"update", "updated", "issue update", "issue updated", "updated issue"}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title-update action when a Linear issue moves to research."""
    if not isinstance(event, Mapping):
        return None

    payload = _merge_payload(event)
    if not _is_status_change_event(payload):
        return None

    status = _new_status(payload)
    if _normalize(status) != _normalize(TARGET_STATUS):
        return None

    issue_id = _first_text(payload, ("id", "issueId", "issue_id", "identifier"))
    title = _first_text(payload, ("title", "name"))
    if issue_id is None or title is None or _has_title_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}{TITLE_SEPARATOR}{title}",
    }


def _merge_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten common automation and Linear webhook wrappers into one payload."""
    payload: dict[str, Any] = {}
    _merge_nested_payload(payload, event)

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        _merge_nested_payload(payload, trigger_context)
        payload.update(trigger_context)

    payload.update(event)
    return payload


def _merge_nested_payload(payload: dict[str, Any], source: Mapping[str, Any]) -> None:
    for key in ("data", "issue"):
        nested = source.get(key)
        if isinstance(nested, Mapping):
            payload.update(nested)

    data = source.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            payload.update(issue)


def _is_status_change_event(payload: Mapping[str, Any]) -> bool:
    event_keys = ("trigger", "event", "eventType", "webhookType", "type", "action")
    normalized_events = {
        normalized
        for key in event_keys
        if (normalized := _normalize(payload.get(key)))
    }

    if normalized_events & STATUS_CHANGE_EVENTS:
        return True

    if any("status changed" in event or "state changed" in event for event in normalized_events):
        return True

    if normalized_events & ISSUE_UPDATE_EVENTS:
        return _updated_fields_include_status(payload)

    return False


def _updated_fields_include_status(payload: Mapping[str, Any]) -> bool:
    updated_fields = payload.get("updatedFields", payload.get("updated_fields"))
    if _fields_include_status(updated_fields):
        return True

    updated_from = payload.get("updatedFrom", payload.get("updated_from"))
    return _fields_include_status(updated_from)


def _fields_include_status(fields: Any) -> bool:
    if isinstance(fields, str):
        field_values: Any = re.split(r"[\s,;]+", fields)
    elif isinstance(fields, Mapping):
        field_values = fields.keys()
    elif isinstance(fields, list | tuple | set):
        field_values = fields
    else:
        return False

    return any(_normalize(field) in STATUS_FIELDS for field in field_values)


def _new_status(payload: Mapping[str, Any]) -> str | None:
    for key in ("newStatus", "new_status"):
        value = _first_text(payload, (key,))
        if value is not None:
            return value

    for key in ("status", "state", "workflowState", "workflow_state"):
        value = _text_or_name(payload.get(key))
        if value is not None:
            return value

    return None


def _first_text(payload: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = _text_or_name(payload.get(key))
        if value is not None:
            return value
    return None


def _text_or_name(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None

    if isinstance(value, Mapping):
        for key in ("name", "title"):
            nested = value.get(key)
            if isinstance(nested, str) and nested.strip():
                return nested.strip()

    return None


def _has_title_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def _normalize(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    value = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    value = re.sub(r"[_\-/]+", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip().lower()


def main() -> int:
    """Read a JSON payload from stdin and print the requested update, if any."""
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON payload: {exc}", file=sys.stderr)
        return 1

    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
