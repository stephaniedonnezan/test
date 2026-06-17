"""Build Linear title updates for Cursor research-status automations."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflow state",
    "workflow status",
    "workflowstate",
    "workflowstatus",
}
_DIRECT_STATUS_EVENTS = {
    "status changed",
    "status change",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
    "workflow status changed",
    "workflow status change",
}
_ISSUE_UPDATE_EVENTS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}
_ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "key", "id")
_STATUS_VALUE_KEYS = (
    "newStatus",
    "new_status",
    "statusName",
    "status_name",
    "newState",
    "new_state",
    "stateName",
    "state_name",
    "newWorkflowState",
    "new_workflow_state",
    "workflowState",
    "workflow_state",
)
_TITLE_KEYS = ("title",)


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear issue-title update action for research status changes.

    The function accepts Cursor automation trigger contexts and common Linear
    webhook shapes. It intentionally returns a plain data structure so the
    caller can decide how to perform the Linear mutation.
    """

    if not isinstance(event, Mapping):
        return None

    is_status_change = _is_direct_status_change_event(event)
    is_generic_status_update = _is_issue_update_event(event) and _has_status_change_marker(event)
    if not is_status_change and not is_generic_status_update:
        return None

    new_status = _extract_new_status(event)
    if _normalize_text(new_status) != TARGET_STATUS:
        return None

    issue_id = _first_present_value(event, _ISSUE_ID_KEYS)
    title = _first_present_value(event, _TITLE_KEYS)
    if issue_id is None or title is None:
        return None

    issue_id = str(issue_id).strip()
    title = str(title).strip()
    if not issue_id or not title or _has_title_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _extract_new_status(event: Mapping[str, Any]) -> Any:
    value = _first_present_value(event, _STATUS_VALUE_KEYS)
    if value is not None:
        return _status_value_name(value)

    value = _status_from_change_objects(event)
    if value is not None:
        return _status_value_name(value)

    # Flat Cursor payloads commonly include the destination status in `status`.
    value = _first_present_value(event, ("status", "state"))
    if value is not None:
        return _status_value_name(value)

    return None


def _status_from_change_objects(event: Mapping[str, Any]) -> Any:
    for mapping in _iter_mappings(event):
        for key in ("changes", "updatedFields"):
            value = mapping.get(key)
            status = _status_from_change_value(value)
            if status is not None:
                return status
    return None


def _status_from_change_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        for key, nested_value in value.items():
            if _is_status_field_name(key):
                status = _status_after_value(nested_value)
                if status is not None:
                    return status
        return None

    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        for item in value:
            status = _status_from_updated_field_item(item)
            if status is not None:
                return status
    return None


def _status_from_updated_field_item(item: Any) -> Any:
    if isinstance(item, str):
        return None
    if not isinstance(item, Mapping):
        return None

    field_name = _first_mapping_value(item, ("name", "field", "key"))
    if not _is_status_field_name(field_name):
        return None

    return _status_after_value(item)


def _status_after_value(value: Any) -> Any:
    if not isinstance(value, Mapping):
        return value

    for key in ("to", "after", "newValue", "new_value", "value", "name"):
        if key in value:
            nested_value = value[key]
            if key == "name":
                return nested_value
            status = _status_after_value(nested_value)
            if status is not None:
                return status
    return _status_value_name(value)


def _status_value_name(value: Any) -> Any:
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            if key in value:
                return value[key]
    return value


def _is_direct_status_change_event(event: Mapping[str, Any]) -> bool:
    for value in _event_descriptor_values(event):
        normalized = _normalize_text(value)
        compact = normalized.replace(" ", "")
        if normalized in _DIRECT_STATUS_EVENTS or compact in {
            "statuschanged",
            "statuschange",
            "statechanged",
            "statechange",
            "workflowstatechanged",
            "workflowstatechange",
            "workflowstatuschanged",
            "workflowstatuschange",
        }:
            return True
    return False


def _is_issue_update_event(event: Mapping[str, Any]) -> bool:
    for value in _event_descriptor_values(event):
        normalized = _normalize_text(value)
        if normalized in _ISSUE_UPDATE_EVENTS:
            return True
    return False


def _has_status_change_marker(event: Mapping[str, Any]) -> bool:
    for mapping in _iter_mappings(event):
        updated_fields = mapping.get("updatedFields")
        if _updated_fields_include_status(updated_fields):
            return True

        changes = mapping.get("changes")
        if isinstance(changes, Mapping) and any(_is_status_field_name(key) for key in changes):
            return True
    return False


def _updated_fields_include_status(updated_fields: Any) -> bool:
    if isinstance(updated_fields, str):
        return _is_status_field_name(updated_fields)
    if isinstance(updated_fields, Iterable):
        for field in updated_fields:
            if isinstance(field, Mapping):
                field = _first_mapping_value(field, ("name", "field", "key"))
            if _is_status_field_name(field):
                return True
    return False


def _event_descriptor_values(event: Mapping[str, Any]) -> Iterable[Any]:
    for mapping in _iter_mappings(event):
        for key in ("trigger", "webhookType", "action", "type"):
            if key in mapping:
                yield mapping[key]


def _first_present_value(event: Mapping[str, Any], keys: Iterable[str]) -> Any:
    for mapping in _preferred_mappings(event):
        value = _first_mapping_value(mapping, keys)
        if value is not None:
            return value
    return None


def _first_mapping_value(mapping: Mapping[str, Any], keys: Iterable[str]) -> Any:
    lowered_keys = {key.lower(): key for key in mapping}
    for key in keys:
        actual_key = lowered_keys.get(key.lower())
        if actual_key is not None:
            value = mapping[actual_key]
            if value is not None:
                return value
    return None


def _preferred_mappings(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    mappings: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in mappings:
            mappings.append(value)

    add(event.get("triggerContext"))
    add(event)

    data = event.get("data")
    issue = event.get("issue")
    if isinstance(data, Mapping):
        add(data.get("issue"))
        add(data)
    add(issue)

    if isinstance(issue, Mapping):
        add(issue.get("state"))
        add(issue.get("workflowState"))
    if isinstance(data, Mapping):
        data_issue = data.get("issue")
        if isinstance(data_issue, Mapping):
            add(data_issue.get("state"))
            add(data_issue.get("workflowState"))

    return mappings


def _iter_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for nested_value in value.values():
            yield from _iter_mappings(nested_value)
    elif isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        for nested_value in value:
            yield from _iter_mappings(nested_value)


def _is_status_field_name(value: Any) -> bool:
    normalized = _normalize_text(value)
    compact = normalized.replace(" ", "")
    return normalized in _STATUS_FIELD_NAMES or compact in _STATUS_FIELD_NAMES


def _has_title_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""

    text = str(value).strip()
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
