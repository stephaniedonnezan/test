"""Build Linear issue title updates for research status changes.

The automation runner can pass either Cursor's flat triggerContext payload or a
nested Linear webhook payload. This module keeps the detection logic small and
side-effect free: callers receive the intended title update action, or ``None``
when the event should be ignored.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


RESEARCH_STATUS = "to research"
TITLE_PREFIX = "Cursor researching"
STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflowstatus"}
STATUS_CHANGE_TRIGGERS = {
    "statuschanged",
    "statuschange",
    "statusupdated",
    "statusupdate",
    "statechanged",
    "statechange",
    "workflowstatechanged",
    "workflowstatechange",
}
GENERIC_UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issueupdated",
    "updatedissue",
    "issueupdate",
}
TRIGGER_KEYS = ("trigger", "webhookType", "action", "type")
EXPLICIT_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "newWorkflowState",
    "new_workflow_state",
    "statusName",
    "status_name",
    "stateName",
    "state_name",
    "workflowStateName",
    "workflow_state_name",
)
DIRECT_STATUS_KEYS = ("status", "state", "workflowState", "workflowStatus")
ISSUE_ID_KEYS = ("issueId", "issue_id", "id", "identifier", "key")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action for research status transitions."""

    if not isinstance(event, Mapping):
        return None

    payload = _unwrap_payload(event)
    if not _is_status_change_event(payload):
        return None

    new_status = _extract_new_status(payload)
    if _normalize_text(new_status) != RESEARCH_STATUS:
        return None

    issue = _issue_payload(payload)
    issue_id = _extract_string(issue, ISSUE_ID_KEYS) or _extract_string(
        payload, ISSUE_ID_KEYS
    )
    title = _extract_string(issue, ("title", "name")) or _extract_string(
        payload, ("title", "name")
    )
    if issue_id is None or title is None:
        return None

    title = title.strip()
    if not title or title.lower().startswith(TITLE_PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _unwrap_payload(event: Mapping[str, Any]) -> Mapping[str, Any]:
    """Prefer automation trigger context, otherwise keep the original payload."""

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        return _merge_payloads(event, trigger_context)
    return event


def _merge_payloads(
    outer: Mapping[str, Any], inner: Mapping[str, Any]
) -> dict[str, Any]:
    merged = dict(inner)
    for key, value in outer.items():
        if key != "triggerContext":
            merged[key] = value
    return merged


def _is_status_change_event(payload: Mapping[str, Any]) -> bool:
    trigger_values = [
        _normalize_token(value)
        for value in _values_for_keys(payload, TRIGGER_KEYS)
        if isinstance(value, str)
    ]

    if any(value in STATUS_CHANGE_TRIGGERS for value in trigger_values):
        return True

    if any(value in GENERIC_UPDATE_TRIGGERS for value in trigger_values):
        return _updated_fields_include_status(payload) or _changes_include_status(
            payload
        )

    return False


def _extract_new_status(payload: Mapping[str, Any]) -> str | None:
    explicit_status = _extract_string(payload, EXPLICIT_STATUS_KEYS)
    if explicit_status is not None:
        return explicit_status

    for change_key in ("changes", "updatedFields"):
        status_from_changes = _status_from_change_container(payload.get(change_key))
        if status_from_changes is not None:
            return status_from_changes

    issue = _issue_payload(payload)
    return _extract_status_from_mapping(issue) or _extract_status_from_mapping(payload)


def _extract_status_from_mapping(payload: Mapping[str, Any]) -> str | None:
    for key in DIRECT_STATUS_KEYS:
        value = payload.get(key)
        status = _status_value_to_string(value)
        if status is not None:
            return status
    return None


def _status_from_change_container(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key, change in value.items():
            if _normalize_field_name(key) in STATUS_FIELD_NAMES:
                status = _status_value_to_string(change)
                if status is not None:
                    return status
                if isinstance(change, Mapping):
                    for candidate_key in ("newValue", "new", "to", "after", "name"):
                        status = _status_value_to_string(change.get(candidate_key))
                        if status is not None:
                            return status
        return None

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for item in value:
            if isinstance(item, str) and _normalize_field_name(item) in STATUS_FIELD_NAMES:
                continue
            if not isinstance(item, Mapping):
                continue
            field_name = _extract_string(item, ("field", "fieldName", "name", "key"))
            if field_name is None or _normalize_field_name(field_name) not in STATUS_FIELD_NAMES:
                continue
            for candidate_key in ("newValue", "new", "to", "after", "value"):
                status = _status_value_to_string(item.get(candidate_key))
                if status is not None:
                    return status
    return None


def _status_value_to_string(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        for key in ("name", "title", "value", "label"):
            string_value = _string_or_none(value.get(key))
            if string_value is not None:
                return string_value
    return None


def _updated_fields_include_status(payload: Mapping[str, Any]) -> bool:
    updated_fields = payload.get("updatedFields")
    if isinstance(updated_fields, Mapping):
        return any(
            _normalize_field_name(key) in STATUS_FIELD_NAMES for key in updated_fields
        )
    if isinstance(updated_fields, Sequence) and not isinstance(
        updated_fields, (str, bytes, bytearray)
    ):
        return any(
            isinstance(field, str)
            and _normalize_field_name(field) in STATUS_FIELD_NAMES
            for field in updated_fields
        )
    return False


def _changes_include_status(payload: Mapping[str, Any]) -> bool:
    changes = payload.get("changes")
    if isinstance(changes, Mapping):
        return any(_normalize_field_name(key) in STATUS_FIELD_NAMES for key in changes)
    if isinstance(changes, Sequence) and not isinstance(
        changes, (str, bytes, bytearray)
    ):
        for change in changes:
            if isinstance(change, Mapping):
                field_name = _extract_string(change, ("field", "fieldName", "name", "key"))
                if field_name and _normalize_field_name(field_name) in STATUS_FIELD_NAMES:
                    return True
    return False


def _issue_payload(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    data = payload.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            return _merge_payloads(payload, issue)
        return _merge_payloads(payload, data)

    issue = payload.get("issue")
    if isinstance(issue, Mapping):
        return _merge_payloads(payload, issue)

    return payload


def _extract_string(payload: Mapping[str, Any], keys: Sequence[str]) -> str | None:
    for key in keys:
        value = _string_or_none(payload.get(key))
        if value is not None:
            return value
    return None


def _string_or_none(value: Any) -> str | None:
    return value if isinstance(value, str) and value.strip() else None


def _values_for_keys(payload: Mapping[str, Any], keys: Sequence[str]) -> list[Any]:
    values = [payload.get(key) for key in keys]
    for nested_key in ("data", "issue"):
        nested = payload.get(nested_key)
        if isinstance(nested, Mapping):
            values.extend(nested.get(key) for key in keys)
    return values


def _normalize_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", _split_camel_case(value).lower())


def _normalize_field_name(value: str) -> str:
    return _normalize_token(value)


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    return re.sub(r"[\s_-]+", " ", _split_camel_case(value).strip().lower())


def _split_camel_case(value: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        json.dump(action, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
