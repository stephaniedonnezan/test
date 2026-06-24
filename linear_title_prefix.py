"""Build Linear issue-title updates for Cursor research status changes.

The automation runtime can provide either a flat Cursor trigger context or a
Linear webhook-shaped payload.  This module keeps the business rule small and
testable: when an issue status changes to "to research", prefix the title with
"Cursor researching".
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_TRIGGER_KEYS = (
    "trigger",
    "webhookType",
    "action",
    "type",
    "event",
    "eventType",
    "webhook_type",
)
_DIRECT_STATUS_CHANGE_EVENTS = {
    "status changed",
    "status change",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
    "workflow status changed",
    "workflow status change",
}
_GENERIC_UPDATE_EVENTS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}
_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflow state",
    "workflow status",
    "workflowstate",
}
_NEW_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "newWorkflowState",
    "new_workflow_state",
    "toStatus",
    "to_status",
    "statusName",
    "status_name",
    "stateName",
    "state_name",
)
_CURRENT_STATUS_KEYS = ("status", "state", "workflowState", "workflow_state")
_ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "key", "id")
_TITLE_KEYS = ("title", "issueTitle", "issue_title")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title-update action for status changes to "to research".

    The returned shape is intentionally simple so an outer automation layer can
    perform the Linear mutation:

    ``{"action": "update_issue_title", "issueId": "POI-123", "title": ...}``
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    status = _extract_new_status(event)
    if _normalize_phrase(status) != TARGET_STATUS:
        return None

    issue_id = _extract_text(event, _ISSUE_ID_KEYS)
    title = _extract_text(event, _TITLE_KEYS)
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


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    event_names = {
        normalized
        for mapping in _candidate_mappings(event)
        for key in _TRIGGER_KEYS
        if (normalized := _normalize_phrase(mapping.get(key)))
    }

    if event_names & _DIRECT_STATUS_CHANGE_EVENTS:
        return True

    if _updated_fields_include_status(event):
        return True

    return bool(event_names & _GENERIC_UPDATE_EVENTS and _status_change_metadata_exists(event))


def _status_change_metadata_exists(event: Mapping[str, Any]) -> bool:
    return _updated_fields_include_status(event) or any(
        _first_status_change_value(mapping) is not None for mapping in _candidate_mappings(event)
    )


def _updated_fields_include_status(event: Mapping[str, Any]) -> bool:
    for mapping in _candidate_mappings(event):
        for key in ("updatedFields", "updated_fields"):
            if _value_mentions_status_field(mapping.get(key)):
                return True

        for key in ("changes", "changed", "updatedFrom", "updated_from"):
            value = mapping.get(key)
            if isinstance(value, Mapping) and _mapping_has_status_key(value):
                return True

    return False


def _extract_new_status(event: Mapping[str, Any]) -> str | None:
    for mapping in _candidate_mappings(event):
        for key in _NEW_STATUS_KEYS:
            status = _coerce_status_name(mapping.get(key))
            if status:
                return status

    for mapping in _candidate_mappings(event):
        status = _first_status_change_value(mapping)
        if status:
            return status

    for mapping in _candidate_mappings(event):
        for key in _CURRENT_STATUS_KEYS:
            status = _coerce_status_name(mapping.get(key))
            if status:
                return status

    return None


def _first_status_change_value(mapping: Mapping[str, Any]) -> str | None:
    for key in ("changes", "changed"):
        value = mapping.get(key)
        if isinstance(value, Mapping):
            status = _status_value_from_change_mapping(value)
            if status:
                return status

    for key in ("updatedFields", "updated_fields"):
        value = mapping.get(key)
        if isinstance(value, Mapping):
            status = _status_value_from_change_mapping(value)
            if status:
                return status

    return None


def _status_value_from_change_mapping(changes: Mapping[str, Any]) -> str | None:
    for key, value in changes.items():
        if not _is_status_field_name(key):
            continue

        if isinstance(value, Mapping):
            for new_value_key in (
                "newValue",
                "new_value",
                "new",
                "to",
                "after",
                "current",
                "name",
            ):
                status = _coerce_status_name(value.get(new_value_key))
                if status:
                    return status

        status = _coerce_status_name(value)
        if status:
            return status

    return None


def _extract_text(event: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for mapping in _candidate_mappings(event):
        for key in keys:
            value = mapping.get(key)
            if isinstance(value, str) and value.strip():
                return value

    return None


def _candidate_mappings(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    mappings: list[Mapping[str, Any]] = [event]

    for key in ("triggerContext", "trigger_context"):
        value = event.get(key)
        if isinstance(value, Mapping):
            mappings.append(value)

    data = event.get("data")
    if isinstance(data, Mapping):
        mappings.append(data)
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            mappings.append(issue)

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        mappings.append(issue)

    return mappings


def _coerce_status_name(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None

    if isinstance(value, Mapping):
        for key in (
            "name",
            "status",
            "state",
            "workflowState",
            "workflow_state",
            "newValue",
            "new_value",
            "new",
            "to",
            "after",
        ):
            status = _coerce_status_name(value.get(key))
            if status:
                return status

    return None


def _value_mentions_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field_name(value)

    if isinstance(value, Mapping):
        return _mapping_has_status_key(value) or any(
            _value_mentions_status_field(item) for item in value.values()
        )

    if isinstance(value, (list, tuple, set)):
        return any(_value_mentions_status_field(item) for item in value)

    return False


def _mapping_has_status_key(value: Mapping[str, Any]) -> bool:
    return any(_is_status_field_name(key) for key in value)


def _is_status_field_name(value: Any) -> bool:
    normalized = _normalize_phrase(value)
    return normalized in _STATUS_FIELD_NAMES


def _normalize_phrase(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    value = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    value = re.sub(r"[^A-Za-z0-9]+", " ", value)
    normalized = " ".join(value.lower().split())
    return normalized or None


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON input: {exc}", file=sys.stderr)
        return 1

    result = build_issue_title_update(event)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
