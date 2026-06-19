"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_DIRECT_STATUS_CHANGE_EVENTS = {
    "status change",
    "status changed",
    "state change",
    "state changed",
    "workflow state change",
    "workflow state changed",
    "issue status change",
    "issue status changed",
    "issue state change",
    "issue state changed",
}

_GENERIC_UPDATE_EVENTS = {
    "issue update",
    "issue updated",
    "update",
    "updated",
    "updated issue",
}

_TRIGGER_KEYS = (
    "trigger",
    "event",
    "eventType",
    "event_type",
    "webhookType",
    "webhook_type",
    "triggerType",
    "trigger_type",
    "action",
    "type",
)

_CONTAINER_KEYS = (
    "automation_trigger_info",
    "automationTriggerInfo",
    "triggerContext",
    "trigger_context",
    "payload",
    "webhook",
    "data",
    "issue",
    "node",
    "resource",
)

_ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "key", "id")
_TITLE_KEYS = ("title", "name", "summary")

_EXPLICIT_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "toStatus",
    "to_status",
    "statusName",
    "status_name",
    "newState",
    "new_state",
    "stateName",
    "state_name",
    "newWorkflowState",
    "new_workflow_state",
    "workflowStateName",
    "workflow_state_name",
)

_FALLBACK_STATUS_KEYS = (
    "status",
    "state",
    "workflowState",
    "workflow_state",
)

_FIELD_LIST_KEYS = (
    "updatedFields",
    "updated_fields",
    "changedFields",
    "changed_fields",
    "changes",
    "changed",
    "updatedFrom",
    "updated_from",
)

_CHANGE_KEYS = (
    "new",
    "to",
    "after",
    "current",
    "value",
    "name",
    "title",
)


def build_issue_title_update(event: Any) -> dict[str, str] | None:
    """Return a title-update action when a Linear issue moves to research."""

    if not isinstance(event, Mapping):
        return None

    contexts = list(_priority_contexts(event))
    if not _is_status_change_event(contexts):
        return None

    new_status = _find_new_status(contexts)
    if _normalize_text(new_status) != TARGET_STATUS:
        return None

    issue_id = _first_text(contexts, _ISSUE_ID_KEYS)
    title = _first_text(contexts, _TITLE_KEYS)
    if not issue_id or not title:
        return None

    stripped_title = title.strip()
    if stripped_title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {stripped_title}",
    }


def _priority_contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely payload containers from outer metadata to nested issue data."""

    seen: set[int] = set()
    queue: list[Any] = [event]

    while queue:
        value = queue.pop(0)
        if not isinstance(value, Mapping):
            continue

        object_id = id(value)
        if object_id in seen:
            continue

        seen.add(object_id)
        yield value

        for key in _CONTAINER_KEYS:
            child = value.get(key)
            if isinstance(child, Mapping):
                queue.append(child)


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    trigger_values = set()
    has_generic_update = False

    for context in contexts:
        for key in _TRIGGER_KEYS:
            normalized = _normalize_text(context.get(key))
            if normalized:
                trigger_values.add(normalized)

    if trigger_values & _DIRECT_STATUS_CHANGE_EVENTS:
        return True

    has_generic_update = bool(trigger_values & _GENERIC_UPDATE_EVENTS)
    return has_generic_update and _has_status_change_marker(contexts)


def _has_status_change_marker(contexts: Iterable[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in _FIELD_LIST_KEYS:
            value = context.get(key)
            if _contains_status_field(value):
                return True
    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field_name(value)

    if isinstance(value, Mapping):
        return any(_is_status_field_name(key) for key in value)

    if isinstance(value, Iterable):
        return any(_contains_status_field(item) for item in value)

    return False


def _is_status_field_name(value: Any) -> bool:
    compact = _normalize_text(value).replace(" ", "")
    return compact in {
        "status",
        "statusid",
        "state",
        "stateid",
        "workflowstate",
        "workflowstateid",
    }


def _find_new_status(contexts: list[Mapping[str, Any]]) -> str | None:
    for keys in (_EXPLICIT_STATUS_KEYS,):
        status = _first_text(contexts, keys)
        if status:
            return status

    status = _status_from_changes(contexts)
    if status:
        return status

    return _first_text(contexts, _FALLBACK_STATUS_KEYS)


def _status_from_changes(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        for key in ("changes", "changed", "updatedFields", "updated_fields"):
            status = _status_from_change_value(context.get(key))
            if status:
                return status
    return None


def _status_from_change_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for field_name, field_value in value.items():
            if _is_status_field_name(field_name):
                return _extract_text(field_value, _CHANGE_KEYS)
        return None

    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        for item in value:
            status = _status_from_change_value(item)
            if status:
                return status

    return None


def _first_text(contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for context in contexts:
        for key in keys:
            text = _extract_text(context.get(key), _CHANGE_KEYS)
            if text:
                return text
    return None


def _extract_text(value: Any, nested_keys: Iterable[str] = ()) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None

    if isinstance(value, (int, float)):
        return str(value)

    if isinstance(value, Mapping):
        for key in nested_keys:
            text = _extract_text(value.get(key), nested_keys)
            if text:
                return text

    return None


def _normalize_text(value: Any) -> str:
    text = _extract_text(value)
    if not text:
        return ""

    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def main() -> int:
    event = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(event), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
