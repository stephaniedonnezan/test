"""Build Linear issue title updates for Cursor research automations."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = ("status", "state", "workflowState", "workflow_state")
STATUS_CHANGE_FIELDS = (*STATUS_FIELDS, "statusId", "stateId", "workflowStateId")
TRIGGER_FIELDS = ("trigger", "webhookType", "webhook_type", "action", "type")
STATUS_VALUE_FIELDS = (
    "newStatus",
    "new_status",
    "toStatus",
    "to_status",
    "status",
    "state",
    "workflowState",
    "workflow_state",
)
ISSUE_ID_FIELDS = ("issueId", "issue_id", "identifier", "key", "id")


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return an issue-title update action when a Linear issue enters research."""
    if not isinstance(event, Mapping):
        return None

    payload = _payload(event)
    issue = _issue(payload)
    merged = {**issue, **payload}

    if not _is_status_change(payload):
        return None

    status = _extract_status(payload)
    if _normalize(status) != TARGET_STATUS:
        return None

    issue_id = _string_from_fields(merged, ISSUE_ID_FIELDS)
    title = _string_from_fields(merged, ("title", "name"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if not title or _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _payload(event: Mapping[str, Any]) -> dict[str, Any]:
    trigger_context = event.get("triggerContext")
    data = event.get("data")

    payload: dict[str, Any] = {}
    if isinstance(data, Mapping):
        payload.update(data)
    if isinstance(trigger_context, Mapping):
        payload.update(trigger_context)
    payload.update(event)
    payload.pop("data", None)
    payload.pop("triggerContext", None)
    return payload


def _issue(payload: Mapping[str, Any]) -> dict[str, Any]:
    issue = payload.get("issue")
    if isinstance(issue, Mapping):
        return dict(issue)
    data = payload.get("data")
    if isinstance(data, Mapping) and isinstance(data.get("issue"), Mapping):
        return dict(data["issue"])
    return {}


def _is_status_change(payload: Mapping[str, Any]) -> bool:
    trigger_values = [
        value
        for field in TRIGGER_FIELDS
        for value in _values_for_key(payload, field)
    ]
    normalized_triggers = {_normalize(value) for value in trigger_values}

    if any(value in {"status changed", "status change", "state changed"} for value in normalized_triggers):
        return True

    if normalized_triggers.intersection({"issue updated", "updated issue", "update", "updated"}):
        return _updated_fields_include_status(payload)

    return False


def _updated_fields_include_status(payload: Mapping[str, Any]) -> bool:
    field_names: list[Any] = []
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        field_names.extend(_coerce_list(payload.get(key)))

    changes = payload.get("changes")
    if isinstance(changes, Mapping):
        field_names.extend(changes.keys())
    elif isinstance(changes, list):
        for change in changes:
            if isinstance(change, Mapping):
                field_names.extend(
                    change.get(key)
                    for key in ("field", "fieldName", "field_name", "name")
                )

    normalized_fields = {_normalize(field) for field in field_names if field}
    return any(_normalize(field) in normalized_fields for field in STATUS_CHANGE_FIELDS)


def _extract_status(payload: Mapping[str, Any]) -> Any:
    for field in ("newStatus", "new_status", "toStatus", "to_status"):
        value = _deep_string(payload.get(field))
        if value:
            return value

    changes = payload.get("changes")
    if isinstance(changes, Mapping):
        for field in STATUS_FIELDS:
            if field in changes:
                value = _change_new_value(changes[field])
                if value:
                    return value
    elif isinstance(changes, list):
        for change in changes:
            if not isinstance(change, Mapping):
                continue
            field_name = _normalize(
                change.get("field")
                or change.get("fieldName")
                or change.get("field_name")
                or change.get("name")
            )
            if field_name in {_normalize(field) for field in STATUS_FIELDS}:
                value = _change_new_value(change)
                if value:
                    return value

    for field in STATUS_VALUE_FIELDS:
        for value in _values_for_key(payload, field):
            status = _deep_string(value)
            if status:
                return status
    return None


def _change_new_value(change: Any) -> str | None:
    if isinstance(change, Mapping):
        for field in ("newValue", "new_value", "to", "after", "value", "name"):
            value = _deep_string(change.get(field))
            if value:
                return value
    return _deep_string(change)


def _values_for_key(value: Any, target_key: str) -> list[Any]:
    if isinstance(value, Mapping):
        values: list[Any] = []
        for key, child in value.items():
            if key == target_key:
                values.append(child)
            values.extend(_values_for_key(child, target_key))
        return values
    if isinstance(value, list):
        values = []
        for child in value:
            values.extend(_values_for_key(child, target_key))
        return values
    return []


def _string_from_fields(payload: Mapping[str, Any], fields: tuple[str, ...]) -> str | None:
    for field in fields:
        value = _deep_string(payload.get(field))
        if value:
            return value
    return None


def _deep_string(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, Mapping):
        for key in ("name", "title", "identifier", "key", "id"):
            nested = _deep_string(value.get(key))
            if nested:
                return nested
    return None


def _coerce_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _normalize(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
