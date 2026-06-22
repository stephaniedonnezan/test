"""Helpers for adding a Cursor research prefix to Linear issue titles."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {"status", "state", "workflow state", "workflowstate"}
_DIRECT_STATUS_TRIGGERS = {
    "status changed",
    "status change",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
}
_UPDATE_TRIGGERS = {
    "issue updated",
    "updated issue",
    "issue update",
    "update",
    "updated",
}
_TRIGGER_KEYS = ("trigger", "webhookType", "action", "type")
_EXPLICIT_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "toStatus",
    "to_status",
    "targetStatus",
    "target_status",
    "newState",
    "new_state",
    "toState",
    "to_state",
)
_FALLBACK_STATUS_KEYS = ("status", "state", "workflowState", "workflow_state")
_TITLE_KEYS = ("title", "name")
_ISSUE_ID_KEYS = ("identifier", "key", "issueId", "issue_id", "id")


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Build an issue-title update action for a Linear "to research" status change.

    The return value is intentionally side-effect free so the caller can decide how
    to apply the update against Linear.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_change_event(contexts):
        return None

    status = _extract_status(contexts)
    if _normalize(status) != TARGET_STATUS:
        return None

    title = _first_text(contexts, _TITLE_KEYS)
    issue_id = _extract_issue_id(contexts)
    if not title or not issue_id:
        return None

    if _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)

    add(event)

    automation_info = event.get("automation_trigger_info")
    if isinstance(automation_info, Mapping):
        add(automation_info)
        add(automation_info.get("triggerContext"))
        add(automation_info.get("trigger_context"))

    add(event.get("triggerContext"))
    add(event.get("trigger_context"))

    data = event.get("data")
    add(data)
    if isinstance(data, Mapping):
        add(data.get("issue"))

    add(event.get("issue"))
    return contexts


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    trigger_names = {
        normalized
        for context in contexts
        for key in _TRIGGER_KEYS
        if (normalized := _normalize(context.get(key)))
    }

    if trigger_names & _DIRECT_STATUS_TRIGGERS:
        return True

    if trigger_names & _UPDATE_TRIGGERS:
        return _changed_fields_include_status(contexts)

    return False


def _changed_fields_include_status(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            if _field_collection_includes_status(context.get(key)):
                return True

        changes = context.get("changes") or context.get("changed")
        if _changes_include_status(changes):
            return True

    return False


def _field_collection_includes_status(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize(value) in _STATUS_FIELD_NAMES

    if isinstance(value, Mapping):
        return any(_normalize(key) in _STATUS_FIELD_NAMES for key in value)

    if isinstance(value, list | tuple | set):
        return any(_field_collection_includes_status(item) for item in value)

    return False


def _changes_include_status(changes: Any) -> bool:
    if isinstance(changes, Mapping):
        for key, value in changes.items():
            if _normalize(key) in _STATUS_FIELD_NAMES:
                return True
            if isinstance(value, Mapping) and _field_collection_includes_status(
                value.get("field") or value.get("fieldName") or value.get("name")
            ):
                return True

    if isinstance(changes, list | tuple):
        return any(_changes_include_status(change) for change in changes)

    return False


def _extract_status(contexts: list[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        for key in _EXPLICIT_STATUS_KEYS:
            status = _text_value(context.get(key))
            if status:
                return status

    for context in contexts:
        status = _status_from_changes(context.get("changes") or context.get("changed"))
        if status:
            return status

    for context in contexts:
        for key in _FALLBACK_STATUS_KEYS:
            status = _text_value(context.get(key))
            if status:
                return status

    return None


def _status_from_changes(changes: Any) -> str | None:
    if isinstance(changes, Mapping):
        for key, value in changes.items():
            if _normalize(key) in _STATUS_FIELD_NAMES:
                status = _new_change_value(value)
                if status:
                    return status
            if isinstance(value, Mapping) and _field_collection_includes_status(
                value.get("field") or value.get("fieldName") or value.get("name")
            ):
                status = _new_change_value(value)
                if status:
                    return status

    if isinstance(changes, list | tuple):
        for change in changes:
            status = _status_from_changes(change)
            if status:
                return status

    return None


def _new_change_value(change: Any) -> str | None:
    if isinstance(change, Mapping):
        for key in ("to", "new", "newValue", "new_value", "after", "value"):
            value = _text_value(change.get(key))
            if value:
                return value
    return _text_value(change)


def _extract_issue_id(contexts: list[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        for key in _ISSUE_ID_KEYS:
            value = _text_value(context.get(key))
            if value:
                return value
    return None


def _first_text(contexts: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for context in contexts:
        for key in keys:
            value = _text_value(context.get(key))
            if value:
                return value
    return None


def _text_value(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "label", "value"):
            text = _text_value(value.get(key))
            if text:
                return text

    return None


def _has_prefix(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())


def _normalize(value: Any) -> str | None:
    text = _text_value(value)
    if not text:
        return None

    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[_\-:/]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip().casefold()
    return text or None


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
