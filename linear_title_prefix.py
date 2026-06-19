"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow state"}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update action when an issue moves to To Research."""
    if not isinstance(event, Mapping):
        return None

    payload = _event_payload(event)
    if not _is_status_change_event(payload):
        return None

    status = _status_value(payload)
    if _normalize_text(status) != TARGET_STATUS:
        return None

    title = _string_value(_first_present(payload, ("title", "name")))
    issue_id = _string_value(
        _first_present(payload, ("issueId", "issue_id", "identifier", "key", "id"))
    )
    if not issue_id or not title:
        return None

    title = title.strip()
    if title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _event_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common Cursor and Linear webhook nesting into one lookup object."""
    payload: dict[str, Any] = {}

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        payload.update(trigger_context)

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            payload.update(issue)
        payload.update(data)

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        payload.update(issue)

    payload.update(event)
    if isinstance(trigger_context, Mapping):
        # Cursor automation metadata should override similarly named issue fields.
        payload.update(trigger_context)

    return payload


def _is_status_change_event(payload: Mapping[str, Any]) -> bool:
    event_names = [
        _normalize_text(payload.get(key))
        for key in ("trigger", "webhookType", "action", "type")
        if payload.get(key) is not None
    ]
    if any(name in {"status changed", "status change", "statuschanged"} for name in event_names):
        return True

    if any(name in {"issue updated", "updated issue", "update"} for name in event_names):
        return _updated_fields_include_status(payload)

    return False


def _updated_fields_include_status(payload: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        fields = payload.get(key)
        if isinstance(fields, str):
            candidates = [fields]
        elif isinstance(fields, Mapping):
            candidates = fields.keys()
        elif isinstance(fields, list | tuple | set):
            candidates = fields
        else:
            continue

        if any(_is_status_field(field) for field in candidates):
            return True

    changes = payload.get("changes") or payload.get("changed")
    if isinstance(changes, Mapping):
        return any(_is_status_field(field) for field in changes)

    return False


def _is_status_field(field: Any) -> bool:
    return _normalize_text(field) in STATUS_FIELDS


def _status_value(payload: Mapping[str, Any]) -> Any:
    explicit_status = _first_present(
        payload,
        (
            "newStatus",
            "new_status",
            "statusName",
            "status_name",
            "newState",
            "new_state",
            "stateName",
            "state_name",
            "workflowStateName",
            "workflow_state_name",
        ),
    )
    if explicit_status is not None:
        return explicit_status

    changes = payload.get("changes") or payload.get("changed")
    if isinstance(changes, Mapping):
        for field, value in changes.items():
            if _is_status_field(field):
                if isinstance(value, Mapping):
                    return _first_present(value, ("to", "new", "after", "name"))
                return value

    for key in ("status", "state", "workflowState", "workflow_state"):
        value = payload.get(key)
        if value is not None:
            return _named_value(value)

    return None


def _named_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return _first_present(value, ("name", "title", "status", "state"))
    return value


def _first_present(payload: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = payload.get(key)
        if value is not None:
            return value
    return None


def _string_value(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    return None


def _normalize_text(value: Any) -> str | None:
    value = _named_value(value)
    if not isinstance(value, str):
        return None

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    normalized = re.sub(r"[^A-Za-z0-9]+", " ", spaced).strip().lower()
    return re.sub(r"\s+", " ", normalized)


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
