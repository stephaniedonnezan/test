"""Build title updates for Linear issues moved into research.

The automation layer can pass either Cursor's flat ``triggerContext`` payload or
Linear's nested issue webhook payload. This module keeps the decision isolated:
return a title-update action only for status/state changes to "to research".
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_DIRECT_STATUS_CHANGE_EVENTS = {
    "status change",
    "status changed",
    "status update",
    "status updated",
    "state change",
    "state changed",
    "workflow state change",
    "workflow state changed",
}
_GENERIC_UPDATE_EVENTS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}
_TRIGGER_KEYS = (
    "trigger",
    "webhookType",
    "webhook_type",
    "action",
    "type",
    "event",
    "eventType",
    "event_type",
)
_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflow state",
    "workflowstate",
    "workflow status",
    "workflowstatus",
}
_NEW_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "toStatus",
    "to_status",
    "targetStatus",
    "target_status",
)
_STATUS_KEYS = (
    "status",
    "state",
    "workflowState",
    "workflow_state",
    "workflowStatus",
    "workflow_status",
)
_ISSUE_ID_KEYS = ("issueId", "issue_id", "id", "identifier", "key")
_TITLE_KEYS = ("title", "name")
_NESTED_CONTEXT_KEYS = (
    "triggerContext",
    "payload",
    "data",
    "issue",
    "node",
    "entity",
    "resource",
)


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue-title update action for Linear "to research" transitions."""

    if not isinstance(event, Mapping):
        return None

    contexts = _candidate_mappings(event)
    if not _is_status_change_event(contexts):
        return None

    new_status = _extract_new_status(contexts)
    if _normalize_text(new_status) != TARGET_STATUS:
        return None

    issue_id = _first_string_value(contexts, _ISSUE_ID_KEYS)
    title = _first_string_value(contexts, _TITLE_KEYS)
    if not issue_id or not title:
        return None

    title = title.strip()
    issue_id = issue_id.strip()
    if not issue_id or not title or _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _candidate_mappings(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []
    seen: set[int] = set()

    def add(value: Any) -> None:
        if not isinstance(value, Mapping):
            return
        object_id = id(value)
        if object_id in seen:
            return
        seen.add(object_id)
        contexts.append(value)

    add(event.get("triggerContext"))
    add(event)

    index = 0
    while index < len(contexts):
        current = contexts[index]
        for key in _NESTED_CONTEXT_KEYS:
            add(current.get(key))
        index += 1

    return contexts


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    saw_generic_update = False

    for context in contexts:
        for key in _TRIGGER_KEYS:
            event_name = _normalize_text(context.get(key))
            if not event_name:
                continue
            if event_name in _DIRECT_STATUS_CHANGE_EVENTS:
                return True
            if "status" in event_name and ("change" in event_name or "update" in event_name):
                return True
            if "state" in event_name and ("change" in event_name or "update" in event_name):
                return True
            if event_name in _GENERIC_UPDATE_EVENTS:
                saw_generic_update = True

    return saw_generic_update and _mentions_status_change(contexts)


def _mentions_status_change(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        if _updated_fields_include_status(context.get("updatedFields")):
            return True
        if _updated_fields_include_status(context.get("updated_fields")):
            return True
        changes = context.get("changes")
        if isinstance(changes, Mapping) and any(_is_status_field(key) for key in changes):
            return True
        if any(key in context for key in _NEW_STATUS_KEYS):
            return True
    return False


def _updated_fields_include_status(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)
    if isinstance(value, Mapping):
        return any(_is_status_field(key) for key in value) or _is_status_field(value)
    if isinstance(value, (list, tuple, set)):
        return any(_updated_fields_include_status(item) for item in value)
    return False


def _is_status_field(value: Any) -> bool:
    return _normalize_text(value) in _STATUS_FIELD_NAMES


def _extract_new_status(contexts: list[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        status = _first_mapping_string(context, _NEW_STATUS_KEYS)
        if status:
            return status

    for context in contexts:
        status = _status_from_changes(context.get("changes"))
        if status:
            return status

    for context in contexts:
        status = _first_mapping_string(context, _STATUS_KEYS)
        if status:
            return status

    return None


def _status_from_changes(changes: Any) -> str | None:
    if not isinstance(changes, Mapping):
        return None

    for key, value in changes.items():
        if not _is_status_field(key):
            continue
        if isinstance(value, Mapping):
            status = _first_mapping_string(
                value,
                ("newValue", "new_value", "to", "after", "current", "value", "name"),
            )
            if status:
                return status
        status = _string_from_value(value)
        if status:
            return status

    return None


def _first_string_value(
    contexts: list[Mapping[str, Any]], keys: tuple[str, ...]
) -> str | None:
    for context in contexts:
        value = _first_mapping_string(context, keys)
        if value:
            return value
    return None


def _first_mapping_string(context: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        if key not in context:
            continue
        value = _string_from_value(context[key])
        if value:
            return value
    return None


def _string_from_value(value: Any) -> str | None:
    if isinstance(value, str):
        value = value.strip()
        return value or None
    if isinstance(value, Mapping):
        return _first_mapping_string(value, ("name", "title", "label", "value", "id"))
    return None


def _normalize_text(value: Any) -> str | None:
    text = _string_from_value(value)
    if text is None:
        return None

    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[_\-/]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip().casefold()


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())


def main() -> int:
    payload = json.load(sys.stdin)
    update = build_issue_title_update(payload)
    if update is not None:
        json.dump(update, sys.stdout, sort_keys=True)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
