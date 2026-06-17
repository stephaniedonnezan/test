"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


TITLE_MARKER = "Cursor researching"
TITLE_PREFIX = f"{TITLE_MARKER}: "
TARGET_STATUS = "to research"

_EVENT_TYPE_KEYS = (
    "trigger",
    "webhookType",
    "webhook_type",
    "action",
    "type",
    "eventType",
    "event_type",
)
_EXPLICIT_NEW_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "toStatus",
    "to_status",
    "newState",
    "new_state",
    "stateName",
    "state_name",
    "statusName",
    "status_name",
    "workflowStateName",
    "workflow_state_name",
)
_STATUS_KEYS = ("status", "state", "workflowState", "workflow_state")
_CHANGED_FIELD_KEYS = (
    "updatedFields",
    "updated_fields",
    "changedFields",
    "changed_fields",
    "updatedProperties",
    "updated_properties",
    "changes",
)
_STATUS_FIELD_NAMES = {"status", "state", "workflowstate"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to "to research".

    The automation runner supplies slightly different payloads depending on the
    trigger source, so this function accepts both flat Cursor trigger contexts
    and nested Linear webhook payloads.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_change_event(contexts):
        return None

    new_status = _new_status(contexts)
    if _normalize_words(new_status) != TARGET_STATUS:
        return None

    issue_id = _text(_first_value(contexts, ("issueId", "issue_id", "identifier", "key", "id")))
    title = _text(_first_value(contexts, ("title", "issueTitle", "issue_title", "name")))
    if not issue_id or not title:
        return None

    clean_title = title.strip()
    if _starts_with_marker(clean_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}{clean_title}",
    }


def handle_issue_status_changed(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Compatibility alias for automation entrypoints."""

    return build_issue_title_update(event)


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return candidate payload contexts in issue-field priority order."""

    contexts: list[Mapping[str, Any]] = []

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        contexts.append(trigger_context)

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        contexts.append(issue)

    data = event.get("data")
    if isinstance(data, Mapping):
        data_issue = data.get("issue")
        if isinstance(data_issue, Mapping):
            contexts.append(data_issue)
        contexts.append(data)

    contexts.append(event)
    return contexts


def _is_status_change_event(contexts: Sequence[Mapping[str, Any]]) -> bool:
    event_types = [_normalize_compact(value) for value in _values(contexts, _EVENT_TYPE_KEYS)]
    has_direct_status_trigger = any(
        event_type in {"statuschanged", "statuschange", "statechanged", "workflowstatechanged"}
        for event_type in event_types
    )
    if has_direct_status_trigger:
        return True

    has_issue_update = any(
        event_type in {"update", "updated"}
        or ("issue" in event_type and ("update" in event_type or "updated" in event_type))
        for event_type in event_types
    )
    return has_issue_update and _mentions_status_field(contexts)


def _new_status(contexts: Sequence[Mapping[str, Any]]) -> str | None:
    for value in _values(contexts, _EXPLICIT_NEW_STATUS_KEYS):
        status = _status_name(value)
        if status:
            return status

    changed_status = _status_from_changes(contexts)
    if changed_status:
        return changed_status

    for value in _values(contexts, _STATUS_KEYS):
        status = _status_name(value)
        if status:
            return status

    return None


def _status_from_changes(contexts: Sequence[Mapping[str, Any]]) -> str | None:
    for changes in _values(contexts, ("changes", "change", "updatedFields", "updated_fields")):
        status = _status_from_change_value(changes)
        if status:
            return status
    return None


def _status_from_change_value(value: Any, field_name: str | None = None) -> str | None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            normalized_key = _normalize_compact(key)
            if normalized_key in _STATUS_FIELD_NAMES:
                status = _status_name(nested)
                if status:
                    return status
            if normalized_key in {"newvalue", "to", "after", "value", "name"}:
                if field_name and _normalize_compact(field_name) in _STATUS_FIELD_NAMES:
                    status = _status_name(nested)
                    if status:
                        return status
            if normalized_key in {"field", "name"} and _normalize_compact(nested) in _STATUS_FIELD_NAMES:
                status = _status_name(value)
                if status:
                    return status
            status = _status_from_change_value(nested, str(key))
            if status:
                return status

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for item in value:
            status = _status_from_change_value(item, field_name)
            if status:
                return status

    return None


def _status_name(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None

    if isinstance(value, Mapping):
        for key in ("newValue", "new_value", "to", "after", "value", "name", "title"):
            status = _status_name(value.get(key))
            if status:
                return status
        for key in _STATUS_KEYS:
            status = _status_name(value.get(key))
            if status:
                return status

    return None


def _mentions_status_field(contexts: Sequence[Mapping[str, Any]]) -> bool:
    for value in _values(contexts, _CHANGED_FIELD_KEYS):
        if any(_normalize_compact(field) in _STATUS_FIELD_NAMES for field in _changed_fields(value)):
            return True
    return False


def _changed_fields(value: Any) -> set[str]:
    fields: set[str] = set()
    if isinstance(value, str):
        fields.add(value)
    elif isinstance(value, Mapping):
        fields.update(str(key) for key in value)
        for key in ("field", "name", "property", "propertyName"):
            nested_value = value.get(key)
            if isinstance(nested_value, str):
                fields.add(nested_value)
        for nested_value in value.values():
            fields.update(_changed_fields(nested_value))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for item in value:
            fields.update(_changed_fields(item))
    return fields


def _values(contexts: Sequence[Mapping[str, Any]], keys: Sequence[str]) -> list[Any]:
    values: list[Any] = []
    for context in contexts:
        for key in keys:
            if key in context:
                values.append(context[key])
    return values


def _first_value(contexts: Sequence[Mapping[str, Any]], keys: Sequence[str]) -> Any:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if _text(value):
                return value
    return None


def _text(value: Any) -> str | None:
    if isinstance(value, str):
        clean = value.strip()
        return clean or None
    return None


def _normalize_words(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value.strip())
    words = re.sub(r"[^A-Za-z0-9]+", " ", spaced).lower().split()
    return " ".join(words)


def _normalize_compact(value: Any) -> str:
    return _normalize_words(value).replace(" ", "")


def _starts_with_marker(title: str) -> bool:
    return title.lower().startswith(TITLE_MARKER.lower())


def main() -> int:
    payload = json.load(sys.stdin)
    result = build_issue_title_update(payload)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
