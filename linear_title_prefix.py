"""Build Linear issue title updates for Cursor research automation.

The automation receives webhook payloads from a few sources/shapes.  This
module keeps the decision pure: return an update action when an issue moves to
"to research", otherwise return None.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue title update action for matching Linear status changes."""
    if not isinstance(event, Mapping):
        return None

    payload = _flatten_payload(event)
    if not _is_status_change_event(payload):
        return None

    status = _status_name(_first_present(payload, ("newStatus", "new_status", "status", "state", "workflowState", "workflow_state")))
    if _normalize_text(status) != TARGET_STATUS:
        return None

    issue_id = _string_value(_first_present(payload, ("issueId", "issue_id", "id", "identifier", "key")))
    title = _string_value(payload.get("title"))
    if not issue_id or not title:
        return None

    if title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _flatten_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common wrapper payloads while keeping top-level trigger metadata."""
    payload: dict[str, Any] = {}

    for key in ("issue", "data", "triggerContext"):
        nested = event.get(key)
        if isinstance(nested, Mapping):
            payload.update(_flatten_payload(nested))

    payload.update(event)
    return payload


def _is_status_change_event(payload: Mapping[str, Any]) -> bool:
    event_names = [
        _normalize_event_name(payload.get(key))
        for key in ("trigger", "webhookType", "action", "type")
        if payload.get(key) is not None
    ]
    event_names = [name for name in event_names if name]

    if any(name in {"statuschanged", "statechanged", "workflowstatechanged"} for name in event_names):
        return True

    if any(name in {"update", "updated", "issueupdated", "updatedissue"} for name in event_names):
        return _status_field_was_updated(payload)

    return False


def _status_field_was_updated(payload: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields"):
        if _contains_status_field(payload.get(key)):
            return True

    changes = payload.get("changes")
    if isinstance(changes, Mapping):
        return any(_normalize_event_name(key) in STATUS_FIELDS for key in changes)

    return _contains_status_field(changes)


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_event_name(value) in STATUS_FIELDS
    if isinstance(value, Mapping):
        return any(_normalize_event_name(key) in STATUS_FIELDS for key in value)
    if isinstance(value, list | tuple | set):
        return any(_contains_status_field(item) for item in value)
    return False


def _first_present(payload: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in payload:
            return payload[key]
    return None


def _status_name(value: Any) -> str | None:
    if isinstance(value, Mapping):
        return _string_value(value.get("name"))
    return _string_value(value)


def _string_value(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    return re.sub(r"[\s_-]+", " ", _split_camel_case(value).strip().lower())


def _normalize_event_name(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return re.sub(r"[^a-z0-9]+", "", _split_camel_case(value).lower())


def _split_camel_case(value: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON payload: {exc}", file=sys.stderr)
        return 1

    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
