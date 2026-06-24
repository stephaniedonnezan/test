"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {"status", "state", "workflow state", "workflowstate"}
_DIRECT_STATUS_TRIGGERS = {
    "status change",
    "status changed",
    "status update",
    "status updated",
    "state change",
    "state changed",
    "workflow state change",
    "workflow state changed",
}
_UPDATE_TRIGGERS = {"update", "updated", "issue update", "issue updated", "updated issue"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear issue title update action when an issue enters research.

    The function accepts the flat Cursor automation trigger payload shape as well
    as nested Linear webhook-style payloads. It is intentionally side-effect free:
    callers can decide how to apply the returned update action.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _event_contexts(event)
    if not _is_status_change_event(contexts):
        return None

    status = _changed_status(contexts)
    if _normalize_text(status) != TARGET_STATUS:
        return None

    issue_id = _first_string(contexts, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_string(contexts, ("title",))
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _event_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Collect likely metadata and issue maps in priority order."""

    contexts: list[Mapping[str, Any]] = []

    def append_mapping(value: Any) -> None:
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)

    automation_info = _mapping_value(event, "automation_trigger_info", "automationTriggerInfo")
    trigger_context = _mapping_value(event, "triggerContext", "trigger_context")
    if automation_info:
        append_mapping(_mapping_value(automation_info, "triggerContext", "trigger_context"))
    append_mapping(trigger_context)

    data = _mapping_value(event, "data")
    issue = _mapping_value(event, "issue")
    data_issue = _mapping_value(data, "issue") if data else None

    append_mapping(data_issue)
    append_mapping(issue)
    append_mapping(data)
    append_mapping(event)
    return contexts


def _mapping_value(mapping: Mapping[str, Any] | None, *keys: str) -> Mapping[str, Any] | None:
    if not isinstance(mapping, Mapping):
        return None
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, Mapping):
            return value
    return None


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    trigger_values = [
        _normalize_text(value)
        for context in contexts
        for key, value in context.items()
        if _normalize_key(key) in {"trigger", "action", "type"}
        and isinstance(value, (str, int, float))
    ]

    if any(value in _DIRECT_STATUS_TRIGGERS for value in trigger_values):
        return True

    has_update_trigger = any(value in _UPDATE_TRIGGERS for value in trigger_values)
    return has_update_trigger and _has_status_change_marker(contexts)


def _has_status_change_marker(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for raw_key, value in context.items():
            key = _normalize_key(raw_key)
            if key in _STATUS_FIELD_NAMES and raw_key not in {"status", "state", "workflowState"}:
                return True
            if key in {"updated fields", "updatedfields", "changed fields", "changedfields"}:
                if _field_collection_mentions_status(value):
                    return True
            if key in {"changes", "change"} and _changes_mention_status(value):
                return True
    return False


def _field_collection_mentions_status(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_key(value) in _STATUS_FIELD_NAMES
    if isinstance(value, Mapping):
        if _normalize_key(value.get("name")) in _STATUS_FIELD_NAMES:
            return True
        return any(_normalize_key(key) in _STATUS_FIELD_NAMES for key in value)
    if isinstance(value, list | tuple | set):
        return any(_field_collection_mentions_status(item) for item in value)
    return False


def _changes_mention_status(value: Any) -> bool:
    if not isinstance(value, Mapping):
        return False
    return any(_normalize_key(key) in _STATUS_FIELD_NAMES for key in value)


def _changed_status(contexts: list[Mapping[str, Any]]) -> Any:
    for context in contexts:
        status = _first_value(context, "newStatus", "new_status", "newState", "new_state")
        if status is not None:
            return _status_name(status)

    for context in contexts:
        changes = _first_value(context, "changes", "change")
        status = _status_from_changes(changes)
        if status is not None:
            return status

    for context in contexts:
        fields = _first_value(context, "updatedFields", "updated_fields", "changedFields", "changed_fields")
        status = _status_from_updated_fields(fields)
        if status is not None:
            return status

    for context in contexts:
        status = _first_value(context, "status", "state", "workflowState", "workflow_state")
        if status is not None:
            return _status_name(status)
    return None


def _status_from_changes(changes: Any) -> Any:
    if not isinstance(changes, Mapping):
        return None
    for key, value in changes.items():
        if _normalize_key(key) not in _STATUS_FIELD_NAMES:
            continue
        if isinstance(value, Mapping):
            return _status_name(_first_value(value, "newValue", "new_value", "to", "after", "current", "name"))
        return _status_name(value)
    return None


def _status_from_updated_fields(fields: Any) -> Any:
    if isinstance(fields, Mapping):
        if _normalize_key(fields.get("name")) in _STATUS_FIELD_NAMES:
            return _status_name(_first_value(fields, "newValue", "new_value", "to", "after", "value", "name"))
        for key, value in fields.items():
            if _normalize_key(key) in _STATUS_FIELD_NAMES:
                return _status_name(value)
    if isinstance(fields, list | tuple | set):
        for item in fields:
            status = _status_from_updated_fields(item)
            if status is not None:
                return status
    return None


def _status_name(value: Any) -> Any:
    if isinstance(value, Mapping):
        return _first_value(value, "name", "displayName", "display_name", "title", "value")
    return value


def _first_value(mapping: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in mapping:
            return mapping[key]
    return None


def _first_string(contexts: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for context in contexts:
        value = _first_value(context, *keys)
        if isinstance(value, (str, int, float)):
            text = str(value).strip()
            if text:
                return text
    return None


def _has_prefix(title: str) -> bool:
    return re.match(rf"^\s*{re.escape(TITLE_PREFIX)}\b", title, flags=re.IGNORECASE) is not None


def _normalize_key(value: Any) -> str:
    normalized = _normalize_text(value)
    return normalized.replace(" ", "") if normalized == "workflow state" else normalized


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def main() -> int:
    event = json.load(sys.stdin)
    result = build_issue_title_update(event)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
