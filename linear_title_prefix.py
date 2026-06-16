"""Build Linear issue-title updates for research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
ACTION = "update_issue_title"

_STATUS_FIELDS = {
    "status",
    "state",
    "workflowstate",
    "workflow_status",
    "workflowstatus",
}
_TRIGGER_FIELDS = ("trigger", "webhookType", "action", "type")
_DIRECT_STATUS_TRIGGERS = {
    "statuschanged",
    "statuschange",
    "statusupdated",
    "statechanged",
    "statechange",
    "workflowstatechanged",
    "workflowstatuschanged",
}
_GENERIC_UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issueupdated",
    "updatedissue",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title-update action when a Linear issue moves to research."""

    if not isinstance(event, Mapping):
        return None

    context = _event_context(event)
    if not _is_status_change_event(context):
        return None

    status = _extract_status(context)
    if _normalize_words(status) != TARGET_STATUS:
        return None

    issue_id = _extract_issue_id(context)
    title = _clean_string(_first_value(context, ("title", "name")))
    if issue_id is None or title is None:
        return None

    return {
        "action": ACTION,
        "issueId": issue_id,
        "title": _prefix_title(title),
    }


def _event_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten common Cursor and Linear webhook payload wrappers."""

    context: dict[str, Any] = {}
    for value in _candidate_mappings(event):
        context.update(value)
    return context


def _candidate_mappings(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    candidates: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in candidates:
            candidates.append(value)

    add(_deep_get(event, ("data", "issue")))
    add(_deep_get(event, ("issue",)))
    add(_deep_get(event, ("triggerContext", "issue")))
    add(_deep_get(event, ("data",)))
    add(_deep_get(event, ("triggerContext",)))
    add(event)
    return candidates


def _is_status_change_event(context: Mapping[str, Any]) -> bool:
    triggers = [
        _normalize_identifier(value)
        for key in _TRIGGER_FIELDS
        if (value := context.get(key)) is not None
    ]
    if any(trigger in _DIRECT_STATUS_TRIGGERS for trigger in triggers):
        return True

    if any(trigger in _GENERIC_UPDATE_TRIGGERS for trigger in triggers):
        return _changed_fields_include_status(context)

    return False


def _changed_fields_include_status(context: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        if _sequence_mentions_status(context.get(key)):
            return True

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        return any(_is_status_field(key) for key in changes)
    if isinstance(changes, Sequence) and not isinstance(changes, (str, bytes, bytearray)):
        return any(_change_mentions_status(change) for change in changes)

    return False


def _sequence_mentions_status(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)
    if not isinstance(value, Sequence) or isinstance(value, (bytes, bytearray)):
        return False
    return any(_change_mentions_status(item) for item in value)


def _change_mentions_status(change: Any) -> bool:
    if isinstance(change, Mapping):
        return any(
            _is_status_field(change.get(key))
            for key in ("field", "fieldName", "name", "key", "property")
        )
    return _is_status_field(change)


def _is_status_field(value: Any) -> bool:
    normalized = _normalize_identifier(value)
    return normalized in _STATUS_FIELDS


def _extract_status(context: Mapping[str, Any]) -> str | None:
    explicit_status = _first_value(
        context,
        (
            "newStatus",
            "new_status",
            "toStatus",
            "to_status",
            "statusName",
            "status_name",
            "stateName",
            "state_name",
            "workflowStateName",
            "workflow_state_name",
        ),
    )
    if (status := _extract_named_value(explicit_status)) is not None:
        return status

    for key in ("changes", "status", "state", "workflowState", "workflow_state"):
        if key == "changes":
            status = _status_from_changes(context.get(key))
        else:
            status = _extract_named_value(context.get(key))
        if status is not None:
            return status

    return None


def _status_from_changes(changes: Any) -> str | None:
    if isinstance(changes, Mapping):
        for key, value in changes.items():
            if _is_status_field(key):
                if (status := _change_new_value(value)) is not None:
                    return status
    elif isinstance(changes, Sequence) and not isinstance(changes, (str, bytes, bytearray)):
        for change in changes:
            if isinstance(change, Mapping) and _change_mentions_status(change):
                if (status := _change_new_value(change)) is not None:
                    return status
    return None


def _change_new_value(change: Any) -> str | None:
    if isinstance(change, Mapping):
        for key in ("newValue", "new_value", "to", "after", "value", "name"):
            if (status := _extract_named_value(change.get(key))) is not None:
                return status
        return None
    return _extract_named_value(change)


def _extract_named_value(value: Any) -> str | None:
    if isinstance(value, str):
        return _clean_string(value)
    if isinstance(value, Mapping):
        return _clean_string(_first_value(value, ("name", "title", "label")))
    return None


def _extract_issue_id(context: Mapping[str, Any]) -> str | None:
    return _clean_string(_first_value(context, ("issueId", "issue_id", "identifier", "key", "id")))


def _first_value(mapping: Mapping[str, Any], keys: Sequence[str]) -> Any:
    for key in keys:
        value = mapping.get(key)
        if value is not None:
            return value
    return None


def _deep_get(mapping: Mapping[str, Any], path: Sequence[str]) -> Any:
    value: Any = mapping
    for key in path:
        if not isinstance(value, Mapping):
            return None
        value = value.get(key)
    return value


def _clean_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _prefix_title(title: str) -> str:
    if title.lower().startswith(PREFIX.lower()):
        return title
    return f"{PREFIX}: {title}"


def _normalize_identifier(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^a-z0-9]", "", _split_camel_case(value).lower())


def _normalize_words(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    normalized = re.sub(r"[^a-z0-9]+", " ", _split_camel_case(value).lower())
    return " ".join(normalized.split())


def _split_camel_case(value: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as error:
        print(f"Invalid JSON: {error}", file=sys.stderr)
        return 1

    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
