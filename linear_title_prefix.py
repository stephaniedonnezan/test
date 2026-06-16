"""Build title update actions for Linear issues entering research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow state"}
_TRIGGER_FIELD_NAMES = (
    "trigger",
    "webhookType",
    "action",
    "type",
    "event",
    "eventType",
)
_EXPLICIT_STATUS_KEYS = (
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
    "toStatus",
    "to_status",
)
_CURRENT_STATUS_KEYS = ("status", "state", "workflowState", "workflow_state")
_TITLE_KEYS = ("title", "name")
_ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "key", "id")


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update action for issues moved to "to research".

    The automation runner passes a compact `triggerContext` payload, while Linear
    webhooks commonly nest issue details under `data.issue`. This accepts both
    shapes and returns None when no title update is needed.
    """
    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    status = _extract_new_status(event)
    if _normalize(status) != TARGET_STATUS:
        return None

    issue_id = _extract_issue_id(event)
    title = _extract_title(event)
    if not issue_id or not title:
        return None

    clean_title = title.strip()
    if clean_title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {clean_title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    trigger_values = [
        _normalize(value)
        for container in _event_containers(event)
        for key in _TRIGGER_FIELD_NAMES
        if (value := container.get(key)) is not None
    ]

    if any(value in {"status changed", "status change", "statuschanged"} for value in trigger_values):
        return True

    is_update_event = any(
        value in {"update", "updated", "issue updated", "updated issue"} for value in trigger_values
    )
    return is_update_event and _payload_mentions_status_change(event)


def _payload_mentions_status_change(event: Mapping[str, Any]) -> bool:
    for container in _event_containers(event):
        for key in ("updatedFields", "updated_fields", "updatedFrom", "updated_from"):
            if _contains_status_field(container.get(key)):
                return True
        if _changes_include_status(container.get("changes")):
            return True
    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_field_name(value) in _STATUS_FIELD_NAMES
    if isinstance(value, Mapping):
        return any(_contains_status_field(key) or _contains_status_field(nested) for key, nested in value.items())
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        return any(_contains_status_field(item) for item in value)
    return False


def _changes_include_status(value: Any) -> bool:
    if isinstance(value, Mapping):
        field = value.get("field") or value.get("fieldName") or value.get("name")
        if field is not None and _contains_status_field(field):
            return True
        return any(_changes_include_status(item) for item in value.values())
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        return any(_changes_include_status(item) for item in value)
    return False


def _extract_new_status(event: Mapping[str, Any]) -> str | None:
    for container in _event_containers(event):
        for key in _EXPLICIT_STATUS_KEYS:
            value = _string_or_name(container.get(key))
            if value:
                return value

    changed_status = _status_from_changes(event)
    if changed_status:
        return changed_status

    for container in _issue_containers(event):
        for key in _CURRENT_STATUS_KEYS:
            value = _string_or_name(container.get(key))
            if value:
                return value
    return None


def _status_from_changes(event: Mapping[str, Any]) -> str | None:
    for container in _event_containers(event):
        value = _status_from_change_value(container.get("changes"))
        if value:
            return value
    return None


def _status_from_change_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        field = value.get("field") or value.get("fieldName") or value.get("name")
        if field is not None and _contains_status_field(field):
            for key in ("newValue", "new_value", "to", "after", "value"):
                status = _string_or_name(value.get(key))
                if status:
                    return status

        for key, nested in value.items():
            if _contains_status_field(key):
                status = _string_or_name(nested)
                if status:
                    return status
            status = _status_from_change_value(nested)
            if status:
                return status

    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        for item in value:
            status = _status_from_change_value(item)
            if status:
                return status

    return None


def _extract_issue_id(event: Mapping[str, Any]) -> str | None:
    for container in _issue_containers(event):
        for key in _ISSUE_ID_KEYS:
            value = container.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _extract_title(event: Mapping[str, Any]) -> str | None:
    for container in _issue_containers(event):
        for key in _TITLE_KEYS:
            value = container.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _event_containers(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    containers: list[Mapping[str, Any]] = [event]

    for key in ("triggerContext", "data"):
        nested = event.get(key)
        if isinstance(nested, Mapping):
            containers.append(nested)

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        containers.append(issue)

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            containers.append(issue)

    return containers


def _issue_containers(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    containers: list[Mapping[str, Any]] = []

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        containers.append(trigger_context)

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        containers.append(issue)

    data = event.get("data")
    if isinstance(data, Mapping):
        data_issue = data.get("issue")
        if isinstance(data_issue, Mapping):
            containers.append(data_issue)
        containers.append(data)

    containers.append(event)
    return containers


def _string_or_name(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        name = value.get("name")
        if isinstance(name, str):
            return name
    return None


def _normalize(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    with_spaces = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    with_spaces = re.sub(r"[^A-Za-z0-9]+", " ", with_spaces)
    return " ".join(with_spaces.lower().split())


def _normalize_field_name(value: Any) -> str:
    return _normalize(value).replace(" ", "")


def main() -> int:
    payload = json.load(sys.stdin)
    action = build_issue_title_update(payload)
    if action is not None:
        print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
