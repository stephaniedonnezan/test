"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_KEYS = {
    "status",
    "state",
    "workflowstate",
    "workflowstatus",
    "statusid",
    "stateid",
    "workflowstateid",
}
_EXPLICIT_STATUS_KEYS = (
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
_STATUS_OBJECT_KEYS = ("status", "state", "workflowState", "workflow_state")
_ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "key", "id")
_TITLE_KEYS = ("title", "name")
_TRIGGER_KEYS = (
    "trigger",
    "webhookTrigger",
    "webhook_trigger",
    "action",
    "event",
    "eventType",
    "event_type",
    "type",
)


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return an issue-title update action when an issue moves to research."""

    if not isinstance(event, Mapping):
        return None

    contexts = _collect_contexts(event)
    if not _is_status_change_event(contexts):
        return None

    new_status = _new_status(contexts)
    if _normalize_value(new_status) != _normalize_value(TARGET_STATUS):
        return None

    issue_id = _first_string(contexts, _ISSUE_ID_KEYS)
    title = _first_string(contexts, _TITLE_KEYS)
    if not issue_id or not title:
        return None

    if title.lower().startswith(PREFIX.lower()):
        prefixed_title = title
    else:
        prefixed_title = f"{PREFIX}: {title}"

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": prefixed_title,
    }


def _collect_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Collect likely event and issue maps from flat and nested webhook payloads."""

    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping):
            contexts.append(value)

    trigger_context = event.get("triggerContext")
    add(trigger_context)

    if isinstance(trigger_context, Mapping):
        add(trigger_context.get("issue"))
        trigger_data = trigger_context.get("data")
        if isinstance(trigger_data, Mapping):
            add(trigger_data.get("issue"))
            add(trigger_data.get("node"))
        add(trigger_data)

    data = event.get("data")
    if isinstance(data, Mapping):
        add(data.get("issue"))
        add(data.get("node"))
    add(event.get("issue"))
    add(event.get("node"))

    add(data)
    add(event)
    return contexts


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    saw_generic_update = False

    for context in contexts:
        for key in _TRIGGER_KEYS:
            trigger_value = context.get(key)
            normalized = _normalize_value(trigger_value)
            compact = normalized.replace(" ", "")
            if compact in {
                "statuschanged",
                "statuschange",
                "statechanged",
                "statechange",
                "workflowstatechanged",
                "workflowstatechange",
            }:
                return True
            if compact in {"issueupdated", "updatedissue", "update", "issueupdate"}:
                saw_generic_update = True

    return saw_generic_update and any(_has_status_change_marker(context) for context in contexts)


def _has_status_change_marker(context: Mapping[str, Any]) -> bool:
    updated_fields = context.get("updatedFields") or context.get("updated_fields")
    if _field_collection_mentions_status(updated_fields):
        return True

    for changes_key in ("changes", "updatedFrom", "updated_from"):
        changes = context.get(changes_key)
        if isinstance(changes, Mapping) and any(_is_status_key(key) for key in changes):
            return True
        if _field_collection_mentions_status(changes):
            return True

    return False


def _new_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    context_list = list(contexts)

    for context in context_list:
        value = _first_value(context, _EXPLICIT_STATUS_KEYS)
        status = _status_name(value)
        if status:
            return status

    for context in context_list:
        for changes_key in ("changes", "updatedFrom", "updated_from"):
            status = _status_from_changes(context.get(changes_key))
            if status:
                return status

    for context in context_list:
        value = _first_value(context, _STATUS_OBJECT_KEYS)
        status = _status_name(value)
        if status:
            return status

    return None


def _status_from_changes(changes: Any) -> str | None:
    if not isinstance(changes, Mapping):
        return None

    for key, value in changes.items():
        if not _is_status_key(key):
            continue
        if isinstance(value, Mapping):
            for new_key in ("new", "to", "after", "current", "value", "name"):
                status = _status_name(value.get(new_key))
                if status:
                    return status
        status = _status_name(value)
        if status:
            return status
    return None


def _field_collection_mentions_status(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_key(value)
    if isinstance(value, Mapping):
        return any(_is_status_key(key) for key in value)
    if isinstance(value, Iterable):
        return any(_is_status_key(item) for item in value)
    return False


def _is_status_key(value: Any) -> bool:
    normalized = _normalize_value(value).replace(" ", "")
    return normalized in _STATUS_KEYS


def _first_string(contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for context in contexts:
        value = _first_value(context, keys)
        if isinstance(value, str):
            stripped = value.strip()
            if stripped:
                return stripped
    return None


def _first_value(context: Mapping[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        if key in context:
            return context[key]
    return None


def _status_name(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    if isinstance(value, Mapping):
        for key in ("name", "title", "status", "state"):
            status = _status_name(value.get(key))
            if status:
                return status
    return None


def _normalize_value(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def main() -> int:
    """Read a JSON event from stdin and print the computed action, if any."""

    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
