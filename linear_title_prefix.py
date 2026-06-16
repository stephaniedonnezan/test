"""Build Linear issue title updates for Cursor research status automations."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}
NEW_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "newWorkflowState",
    "new_workflow_state",
)
CURRENT_STATUS_KEYS = (
    "status",
    "state",
    "workflowState",
    "workflow_state",
)
TRIGGER_KEYS = ("trigger", "webhookType", "webhook_type", "action", "type")
STATUS_CHANGE_TRIGGERS = {
    "status changed",
    "statuschanged",
    "state changed",
    "statechanged",
    "workflow state changed",
    "workflowstatechanged",
}
GENERIC_UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return the title update action for issues moved to To Research."""

    if not isinstance(event, Mapping):
        return None

    payload = _normalized_payload(event)
    if not _is_status_change_event(payload):
        return None

    status = _changed_status(payload)
    if _normalize_status(status) != TARGET_STATUS:
        return None

    issue_id = _clean_text(_first_value(payload, ("id", "issueId", "issue_id", "identifier", "key")))
    title = _clean_text(_first_value(payload, ("title", "name")))
    if not issue_id or not title or _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _normalized_payload(event: Mapping[str, Any]) -> dict[str, Any]:
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
    return payload


def _is_status_change_event(payload: Mapping[str, Any]) -> bool:
    trigger_values = [
        _normalize_label(value)
        for key in TRIGGER_KEYS
        if (value := payload.get(key)) is not None
    ]

    if any(value in STATUS_CHANGE_TRIGGERS for value in trigger_values):
        return True

    if any(value in GENERIC_UPDATE_TRIGGERS for value in trigger_values):
        return _changed_fields_include_status(payload) or _changes_include_status(payload)

    return False


def _changed_status(payload: Mapping[str, Any]) -> Any:
    for key in NEW_STATUS_KEYS:
        value = _status_name(payload.get(key))
        if value:
            return value

    for key in ("changes", "change"):
        value = _status_from_changes(payload.get(key))
        if value:
            return value

    for key in CURRENT_STATUS_KEYS:
        value = _status_name(payload.get(key))
        if value:
            return value

    return None


def _changed_fields_include_status(payload: Mapping[str, Any]) -> bool:
    fields = payload.get("updatedFields") or payload.get("changedFields") or payload.get("updated_fields")
    return _fields_include_status(fields)


def _fields_include_status(fields: Any) -> bool:
    if isinstance(fields, str):
        return _field_is_status(fields)
    if isinstance(fields, Mapping):
        return any(_field_is_status(key) for key in fields)
    if isinstance(fields, list | tuple | set):
        return any(_field_is_status(field) for field in fields)
    return False


def _changes_include_status(payload: Mapping[str, Any]) -> bool:
    return any(_status_from_changes(payload.get(key)) for key in ("changes", "change"))


def _status_from_changes(changes: Any) -> Any:
    if isinstance(changes, Mapping):
        for key, value in changes.items():
            if _field_is_status(key):
                return _new_value(value)
    elif isinstance(changes, list | tuple):
        for change in changes:
            if not isinstance(change, Mapping):
                continue
            field = change.get("field") or change.get("key") or change.get("name")
            if _field_is_status(field):
                return _new_value(change)
    return None


def _new_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        for key in ("newValue", "new_value", "to", "after", "value", "name"):
            if (candidate := _status_name(value.get(key))) is not None:
                return candidate
    return _status_name(value)


def _status_name(value: Any) -> Any:
    if isinstance(value, Mapping):
        return value.get("name") or value.get("title") or value.get("value")
    return value


def _first_value(payload: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = payload.get(key)
        if value is not None:
            return value
    return None


def _clean_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _has_prefix(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())


def _field_is_status(value: Any) -> bool:
    return _normalize_field(value) in STATUS_FIELDS


def _normalize_field(value: Any) -> str:
    return re.sub(r"[^a-z]", "", _split_camel(value).casefold()) if isinstance(value, str) else ""


def _normalize_status(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return _normalize_label(value)


def _normalize_label(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    spaced = _split_camel(value)
    return re.sub(r"\s+", " ", re.sub(r"[_-]+", " ", spaced).strip().casefold())


def _split_camel(value: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)


def main() -> int:
    event = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(event), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
