"""Build Linear issue title updates for Cursor research automations."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


RESEARCH_STATUS = "to research"
TITLE_PREFIX = "Cursor researching"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflowstatus"}
STATUS_CHANGE_EVENTS = {
    "statuschanged",
    "statuschange",
    "status changed",
    "status_changed",
    "statechanged",
    "statechange",
    "state changed",
    "state_changed",
    "workflowstatechanged",
    "workflow state changed",
    "workflow_state_changed",
}
ISSUE_UPDATE_EVENTS = {
    "update",
    "updated",
    "issueupdate",
    "issueupdated",
    "issue update",
    "issue updated",
    "updatedissue",
    "updated issue",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to To Research."""
    if not isinstance(event, Mapping):
        return None

    payload = _coerce_payload(event)
    if not _is_status_change_event(payload):
        return None

    status = _extract_new_status(payload)
    if _normalize_status(status) != RESEARCH_STATUS:
        return None

    issue_id = _extract_issue_id(payload)
    title = _extract_title(payload)
    if not issue_id or not title or _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _coerce_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten common Cursor and Linear webhook shapes into a single mapping."""
    payload: dict[str, Any] = {}

    for container_key in ("data", "issue", "triggerContext"):
        container = event.get(container_key)
        if isinstance(container, Mapping):
            payload.update(_coerce_payload(container))

    automation_info = event.get("automation_trigger_info")
    if isinstance(automation_info, Mapping):
        trigger_context = automation_info.get("triggerContext")
        if isinstance(trigger_context, Mapping):
            payload.update(_coerce_payload(trigger_context))

    payload.update(event)
    return payload


def _is_status_change_event(payload: Mapping[str, Any]) -> bool:
    event_names = [
        _normalize_token(value)
        for key in ("trigger", "webhookType", "action", "type", "event")
        if (value := _string_value(payload.get(key)))
    ]
    if any(name in STATUS_CHANGE_EVENTS for name in event_names):
        return True
    if any(name in ISSUE_UPDATE_EVENTS for name in event_names):
        return _updated_fields_include_status(payload)
    return False


def _updated_fields_include_status(payload: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        fields = payload.get(key)
        if _fields_include_status(fields):
            return True

    changes = payload.get("changes")
    if isinstance(changes, Mapping):
        return any(_is_status_field(field) for field in changes)
    if isinstance(changes, Iterable) and not isinstance(changes, (str, bytes, Mapping)):
        return any(_change_mentions_status(change) for change in changes)

    return False


def _fields_include_status(fields: Any) -> bool:
    if isinstance(fields, str):
        return _is_status_field(fields)
    if isinstance(fields, Iterable) and not isinstance(fields, (bytes, Mapping)):
        return any(_is_status_field(_string_value(field)) for field in fields)
    return False


def _change_mentions_status(change: Any) -> bool:
    if isinstance(change, Mapping):
        return any(_is_status_field(_string_value(change.get(key))) for key in ("field", "name", "key"))
    return _is_status_field(_string_value(change))


def _is_status_field(field: str | None) -> bool:
    return bool(field and _normalize_field_name(field) in STATUS_FIELDS)


def _extract_new_status(payload: Mapping[str, Any]) -> str | None:
    for key in (
        "newStatus",
        "new_status",
        "statusName",
        "status_name",
        "stateName",
        "state_name",
        "workflowStateName",
        "workflow_state_name",
    ):
        if value := _string_value(payload.get(key)):
            return value

    changes = payload.get("changes")
    if isinstance(changes, Mapping):
        for field, change in changes.items():
            if _is_status_field(_string_value(field)):
                if status := _status_from_change(change):
                    return status
    elif isinstance(changes, Iterable) and not isinstance(changes, (str, bytes, Mapping)):
        for change in changes:
            if isinstance(change, Mapping) and _change_mentions_status(change):
                if status := _status_from_change(change):
                    return status

    for key in ("status", "state", "workflowState", "workflow_state"):
        if status := _status_from_value(payload.get(key)):
            return status

    return None


def _status_from_change(change: Any) -> str | None:
    if isinstance(change, Mapping):
        for key in ("to", "toValue", "newValue", "after", "value", "name"):
            if status := _status_from_value(change.get(key)):
                return status
    return _status_from_value(change)


def _status_from_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            if status := _string_value(value.get(key)):
                return status
        return None
    return _string_value(value)


def _extract_issue_id(payload: Mapping[str, Any]) -> str | None:
    for key in ("issueId", "issue_id", "identifier", "key", "id"):
        if issue_id := _string_value(payload.get(key)):
            return issue_id
    return None


def _extract_title(payload: Mapping[str, Any]) -> str | None:
    for key in ("title", "name"):
        if title := _string_value(payload.get(key)):
            return title
    return None


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(TITLE_PREFIX.casefold())


def _normalize_status(status: str | None) -> str | None:
    if not status:
        return None
    words = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", status)
    return re.sub(r"[\W_]+", " ", words).strip().casefold()


def _normalize_token(value: str) -> str:
    words = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", value)
    return re.sub(r"[\W_]+", " ", words).strip().casefold()


def _normalize_field_name(value: str) -> str:
    words = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", value)
    normalized = re.sub(r"[\W_]+", " ", words).strip().casefold()
    return normalized.replace(" ", "")


def _string_value(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def main() -> int:
    update = build_issue_title_update(json.load(sys.stdin))
    if update is not None:
        print(json.dumps(update, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
