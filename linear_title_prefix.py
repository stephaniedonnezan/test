"""Build Linear issue title updates for research status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_TRIGGER_KEYS = {"trigger", "webhook type", "action", "type"}
_DIRECT_STATUS_CHANGE_TRIGGERS = {
    "status changed",
    "status change",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
    "issue status changed",
    "issue status change",
}
_GENERIC_UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}
_STATUS_FIELDS = {"status", "state", "workflow state", "workflow status"}
_EXPLICIT_STATUS_KEYS = {
    "new status",
    "new state",
    "new workflow state",
    "new workflow status",
    "status name",
    "state name",
    "workflow state name",
    "workflow status name",
    "to status",
    "to state",
}
_ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "key", "id")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to to research."""

    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_change_event(contexts):
        return None

    status = _extract_new_status(contexts)
    if _normalize_text(status) != TARGET_STATUS:
        return None

    issue_id = _extract_issue_id(contexts)
    title = _extract_title(contexts)
    if not issue_id or not title:
        return None

    clean_title = title.strip()
    if clean_title.lower().startswith(TITLE_PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {clean_title}",
    }


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []
    seen: set[int] = set()

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and id(value) not in seen:
            seen.add(id(value))
            contexts.append(value)

    add(event)
    trigger_context = event.get("triggerContext")
    add(trigger_context)

    automation_info = event.get("automation_trigger_info") or event.get("automationTriggerInfo")
    add(automation_info)
    if isinstance(automation_info, Mapping):
        add(automation_info.get("triggerContext"))

    data = event.get("data")
    add(data)
    if isinstance(data, Mapping):
        add(data.get("issue"))

    add(event.get("issue"))

    return contexts


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    generic_update_seen = False

    for context in contexts:
        for key, value in context.items():
            if _normalize_text(key) not in _TRIGGER_KEYS:
                continue
            normalized_value = _normalize_text(value)
            if normalized_value in _DIRECT_STATUS_CHANGE_TRIGGERS:
                return True
            if normalized_value in _GENERIC_UPDATE_TRIGGERS:
                generic_update_seen = True

    return generic_update_seen and _mentions_status_update(contexts)


def _mentions_status_update(contexts: Iterable[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            if _contains_status_field(context.get(key)):
                return True

        changes = context.get("changes")
        if isinstance(changes, Mapping):
            if any(_is_status_field(key) for key in changes):
                return True
        elif _contains_status_field(changes):
            return True

    return False


def _extract_new_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    context_list = list(contexts)

    for context in context_list:
        for key, value in context.items():
            if _normalize_text(key) in _EXPLICIT_STATUS_KEYS:
                status = _status_name(value)
                if status:
                    return status

    for context in context_list:
        status = _status_from_changes(context.get("changes"))
        if status:
            return status

    for context in context_list:
        for key, value in context.items():
            if _is_status_field(key):
                status = _status_name(value)
                if status:
                    return status

    return None


def _status_from_changes(changes: Any) -> str | None:
    if isinstance(changes, Mapping):
        for key, value in changes.items():
            if not _is_status_field(key):
                continue
            return _changed_status_value(value)
    elif isinstance(changes, list):
        for change in changes:
            if isinstance(change, Mapping):
                field = (
                    change.get("field")
                    or change.get("fieldName")
                    or change.get("name")
                    or change.get("key")
                )
                if field and _is_status_field(field):
                    status = _changed_status_value(change)
                    if status:
                        return status
            elif _is_status_field(change):
                return None

    return None


def _changed_status_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("newValue", "new_value", "to", "after", "new", "current", "name"):
            status = _status_name(value.get(key))
            if status:
                return status
    return _status_name(value)


def _extract_issue_id(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        for key in _ISSUE_ID_KEYS:
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _extract_title(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        value = context.get("title")
        if isinstance(value, str) and value.strip():
            return value
    return None


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)
    if isinstance(value, Mapping):
        field = (
            value.get("field")
            or value.get("fieldName")
            or value.get("name")
            or value.get("key")
        )
        if field and _is_status_field(field):
            return True
        return any(_contains_status_field(item) for item in value.values())
    if isinstance(value, list | tuple | set):
        return any(_contains_status_field(item) for item in value)
    return False


def _is_status_field(value: Any) -> bool:
    return _normalize_text(value) in _STATUS_FIELDS


def _status_name(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, Mapping):
        for key in ("name", "title", "status", "state", "workflowState", "workflow_state"):
            status = _status_name(value.get(key))
            if status:
                return status
    return None


def _normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    words = re.sub(r"[^A-Za-z0-9]+", " ", spaced).strip().lower()
    return re.sub(r"\s+", " ", words)


def main() -> None:
    """Read a JSON event from stdin and print the requested title update."""

    event = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(event), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
