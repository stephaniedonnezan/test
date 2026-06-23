"""Build Linear issue-title updates for research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"

_DIRECT_STATUS_TRIGGERS = {
    "status changed",
    "status change",
    "issue status changed",
    "state changed",
    "workflow state changed",
}
_GENERIC_UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}
_TRIGGER_KEYS = {
    "action",
    "event",
    "eventType",
    "trigger",
    "triggerType",
    "type",
    "webhookType",
}
_EXPLICIT_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "statusName",
    "stateName",
    "workflowStateName",
)
_STATUS_KEYS = ("status", "state", "workflowState", "workflow_state")
_ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "key")


def build_issue_title_update(event: Any) -> dict[str, str] | None:
    """Return an issue-title update action when a payload moves to research."""

    if not isinstance(event, Mapping):
        return None

    contexts = _collect_contexts(event)
    if not _is_status_change_event(contexts):
        return None

    status = _extract_new_status(contexts)
    if _normalize_words(status) != TARGET_STATUS:
        return None

    title = _extract_title(contexts)
    issue_id = _extract_issue_id(contexts)
    if not title or not issue_id or _has_prefix(title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def handle_issue_status_changed(event: Any) -> dict[str, str] | None:
    """Compatibility wrapper for callers that name the handler by the trigger."""

    return build_issue_title_update(event)


def _collect_contexts(event: Mapping[str, Any]) -> list[tuple[tuple[str, ...], Mapping[str, Any]]]:
    contexts: list[tuple[tuple[str, ...], Mapping[str, Any]]] = []
    seen: set[int] = set()
    nested_keys = (
        "automation_trigger_info",
        "automationTriggerInfo",
        "triggerContext",
        "trigger_context",
        "payload",
        "data",
        "issue",
    )

    def walk(value: Any, path: tuple[str, ...]) -> None:
        if not isinstance(value, Mapping) or id(value) in seen:
            return

        seen.add(id(value))
        contexts.append((path, value))
        for key in nested_keys:
            if key in value:
                walk(value[key], path + (key,))

    walk(event, ())
    return contexts


def _is_status_change_event(contexts: list[tuple[tuple[str, ...], Mapping[str, Any]]]) -> bool:
    trigger_names = {
        _normalize_words(value)
        for _, context in contexts
        for key, value in context.items()
        if key in _TRIGGER_KEYS and isinstance(value, str)
    }

    if trigger_names & _DIRECT_STATUS_TRIGGERS:
        return True

    if trigger_names & _GENERIC_UPDATE_TRIGGERS:
        return _has_status_update_marker(contexts)

    return False


def _has_status_update_marker(contexts: list[tuple[tuple[str, ...], Mapping[str, Any]]]) -> bool:
    return any(
        _updated_fields_include_status(context.get(key))
        for _, context in contexts
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields", "changes")
    ) or any(
        old_key in context and new_key in context
        for _, context in contexts
        for old_key, new_key in (
            ("oldStatus", "newStatus"),
            ("previousStatus", "newStatus"),
            ("old_state", "new_state"),
        )
    )


def _updated_fields_include_status(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)
    if isinstance(value, Mapping):
        return any(_is_status_field(str(key)) for key in value)
    if isinstance(value, list | tuple | set):
        return any(
            _is_status_field(item)
            or (isinstance(item, Mapping) and _change_item_mentions_status(item))
            for item in value
        )
    return False


def _change_item_mentions_status(change: Mapping[str, Any]) -> bool:
    return any(
        _is_status_field(value)
        for key in ("field", "fieldName", "name", "property")
        if isinstance((value := change.get(key)), str)
    )


def _is_status_field(value: Any) -> bool:
    if not isinstance(value, str):
        return False

    compact = _normalize_field(value)
    return compact in {
        "status",
        "statusid",
        "state",
        "stateid",
        "workflowstate",
        "workflowstateid",
        "workflowstatus",
        "workflowstatusid",
    }


def _extract_new_status(contexts: list[tuple[tuple[str, ...], Mapping[str, Any]]]) -> str | None:
    for _, context in contexts:
        for key in _EXPLICIT_STATUS_KEYS:
            status = _string_or_named_value(context.get(key))
            if status:
                return status

    for _, context in contexts:
        status = _status_from_changes(context.get("changes"))
        if status:
            return status

    for path, context in _prioritized_issue_contexts(contexts):
        for key in _STATUS_KEYS:
            status = _string_or_named_value(context.get(key))
            if status:
                return status
        if path and path[-1] in {"state", "workflowState", "workflow_state"}:
            status = _string_or_named_value(context)
            if status:
                return status

    return None


def _status_from_changes(changes: Any) -> str | None:
    if isinstance(changes, Mapping):
        for key, value in changes.items():
            if not _is_status_field(str(key)):
                continue
            status = _new_value_from_change(value)
            if status:
                return status
    elif isinstance(changes, list | tuple):
        for change in changes:
            if not isinstance(change, Mapping) or not _change_item_mentions_status(change):
                continue
            status = _new_value_from_change(change)
            if status:
                return status
    return None


def _new_value_from_change(change: Any) -> str | None:
    if isinstance(change, str):
        return change.strip() or None
    if not isinstance(change, Mapping):
        return None

    for key in ("newValue", "new_value", "to", "after", "current", "name"):
        status = _string_or_named_value(change.get(key))
        if status:
            return status
    return None


def _extract_title(contexts: list[tuple[tuple[str, ...], Mapping[str, Any]]]) -> str | None:
    for _, context in _prioritized_issue_contexts(contexts):
        title = _clean_string(context.get("title"))
        if title:
            return title
    return None


def _extract_issue_id(contexts: list[tuple[tuple[str, ...], Mapping[str, Any]]]) -> str | None:
    for _, context in _prioritized_issue_contexts(contexts):
        for key in _ISSUE_ID_KEYS:
            issue_id = _clean_string(context.get(key))
            if issue_id:
                return issue_id

    for _, context in _prioritized_issue_contexts(contexts):
        issue_id = _clean_string(context.get("id"))
        if issue_id:
            return issue_id

    return None


def _prioritized_issue_contexts(
    contexts: list[tuple[tuple[str, ...], Mapping[str, Any]]],
) -> list[tuple[tuple[str, ...], Mapping[str, Any]]]:
    def priority(item: tuple[tuple[str, ...], Mapping[str, Any]]) -> tuple[int, int]:
        path, context = item
        path_text = ".".join(path)
        if "issue" in path:
            return (0, len(path))
        if path_text.endswith("triggerContext") or path_text.endswith("trigger_context"):
            return (1, len(path))
        if "title" in context or any(key in context for key in _ISSUE_ID_KEYS):
            return (2, len(path))
        return (3, len(path))

    return sorted(contexts, key=priority)


def _string_or_named_value(value: Any) -> str | None:
    if isinstance(value, str):
        return _clean_string(value)
    if isinstance(value, Mapping):
        for key in ("name", "title", "status", "state"):
            text = _string_or_named_value(value.get(key))
            if text:
                return text
    return None


def _has_prefix(title: str) -> bool:
    return title.strip().lower().startswith(PREFIX.lower())


def _clean_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    value = value.strip()
    return value or None


def _normalize_words(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    value = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    value = re.sub(r"[^A-Za-z0-9]+", " ", value)
    return " ".join(value.lower().split())


def _normalize_field(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", _normalize_words(value))


def main() -> int:
    event = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(event), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
