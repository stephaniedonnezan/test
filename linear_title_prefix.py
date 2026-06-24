"""Build Linear issue title updates for research-status automations."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflowstate",
    "workflow_status",
    "workflowstatus",
}
STATUS_TRIGGER_VALUES = {
    "statuschanged",
    "statuschange",
    "statusupdated",
    "statusupdate",
    "statechanged",
    "statechange",
    "workflowstatechanged",
    "workflowstatechange",
}
ISSUE_UPDATE_VALUES = {
    "update",
    "updated",
    "issueupdate",
    "issueupdated",
    "updatedissue",
}
NEW_STATUS_KEYS = (
    "newStatus",
    "new_status",
)
CURRENT_STATUS_KEYS = (
    "status",
    "state",
    "workflowState",
    "workflow_status",
)
ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "key", "id")


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title-update action for issues moved to research."""

    if not isinstance(event, Mapping):
        return None

    context = _merged_context(event)
    if not _is_status_change_event(context):
        return None

    status = _extract_new_status(context)
    if _normalize_status(status) != TARGET_STATUS:
        return None

    issue_id = _clean_string(_first_from_payloads(event, ISSUE_ID_KEYS))
    title = _clean_string(_first_from_payloads(event, ("title", "name")))
    if not issue_id or not title:
        return None

    if _has_prefix(title):
        prefixed_title = title
    else:
        prefixed_title = f"{PREFIX}: {title}"

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": prefixed_title,
    }


def _merged_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common Cursor and Linear webhook envelopes into one lookup map."""

    context: dict[str, Any] = {}

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        context.update(_issue_fields_from(trigger_context))
        context.update(trigger_context)

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            context.update(_issue_fields_from(issue))
            context.update(issue)

        context.update(_issue_fields_from(data))
        context.update(data)

    context.update(_issue_fields_from(event))
    context.update(event)
    return context


def _issue_fields_from(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields: dict[str, Any] = {}

    issue = payload.get("issue")
    if isinstance(issue, Mapping):
        fields.update(_issue_fields_from(issue))
        fields.update(issue)

    for field_name in ("state", "workflowState", "workflow_status"):
        value = payload.get(field_name)
        if isinstance(value, Mapping):
            name = _clean_string(value.get("name"))
            if name:
                fields[field_name] = name

    return fields


def _is_status_change_event(context: Mapping[str, Any]) -> bool:
    trigger_values = _all_trigger_values(context)
    if any(value in STATUS_TRIGGER_VALUES for value in trigger_values):
        return True

    if not any(value in ISSUE_UPDATE_VALUES for value in trigger_values):
        return False

    return _has_updated_status_field(context)


def _all_trigger_values(context: Mapping[str, Any]) -> set[str]:
    values: set[str] = set()
    for key in ("trigger", "webhookType", "action", "type"):
        raw_value = context.get(key)
        if isinstance(raw_value, str):
            values.add(_normalize_token(raw_value))
    return values


def _has_updated_status_field(context: Mapping[str, Any]) -> bool:
    updated_fields = context.get("updatedFields")
    if isinstance(updated_fields, str):
        if _is_status_field_name(updated_fields):
            return True
    elif isinstance(updated_fields, list):
        if any(_is_status_field_name(field) for field in updated_fields):
            return True

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        return any(_is_status_field_name(field) for field in changes)

    return False


def _is_status_field_name(field: Any) -> bool:
    if not isinstance(field, str):
        return False
    normalized = _normalize_field_name(field)
    return normalized in STATUS_FIELD_NAMES


def _extract_new_status(context: Mapping[str, Any]) -> str | None:
    for key in NEW_STATUS_KEYS:
        value = context.get(key)
        status = _status_name(value)
        if status:
            return status

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        for key in ("status", "state", "workflowState"):
            status = _changed_status_name(changes.get(key))
            if status:
                return status

    updated_fields = context.get("updatedFields")
    if isinstance(updated_fields, Mapping):
        for key in ("status", "state", "workflowState"):
            status = _changed_status_name(updated_fields.get(key))
            if status:
                return status

    for key in CURRENT_STATUS_KEYS:
        value = context.get(key)
        status = _status_name(value)
        if status:
            return status

    return None


def _status_name(value: Any) -> str | None:
    if isinstance(value, str):
        return _clean_string(value)
    if isinstance(value, Mapping):
        for key in ("name", "newValue", "new_value", "to"):
            status = _status_name(value.get(key))
            if status:
                return status
    return None


def _changed_status_name(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("newValue", "new_value", "to", "after", "name"):
            status = _status_name(value.get(key))
            if status:
                return status
    return _status_name(value)


def _first_present(context: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = context.get(key)
        if value is not None:
            return value
    return None


def _first_from_payloads(event: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    for payload in _issue_payloads(event):
        value = _first_present(payload, keys)
        if value is not None:
            return value
    return None


def _issue_payloads(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    payloads: list[Mapping[str, Any]] = []

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        payloads.append(trigger_context)
        issue = trigger_context.get("issue")
        if isinstance(issue, Mapping):
            payloads.append(issue)

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            payloads.append(issue)
        payloads.append(data)

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        payloads.append(issue)

    payloads.append(event)
    return payloads


def _clean_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def _has_prefix(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())


def _normalize_status(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return re.sub(r"[^a-z0-9]+", " ", _split_camel(value).casefold()).strip()


def _normalize_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", _split_camel(value).casefold())


def _normalize_field_name(value: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "", _split_camel(value).casefold())


def _split_camel(value: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)


def main() -> int:
    """Read an event JSON document from stdin and print the action, if any."""

    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
