"""Build issue title updates for Linear research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_CHANGED_TRIGGERS = {
    "status change",
    "status changed",
    "state change",
    "state changed",
    "workflow state change",
    "workflow state changed",
}
_ISSUE_UPDATED_TRIGGERS = {
    "issue update",
    "issue updated",
    "update",
    "updated",
    "updated issue",
}
_STATUS_FIELD_NAMES = {"state", "status", "workflowstate"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when an issue moves to To Research."""

    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_change_event(contexts):
        return None

    status = _status_name(contexts)
    if _normalize_words(status) != TARGET_STATUS:
        return None

    issue_id = _first_string(contexts, ("id", "issueId", "issue_id", "identifier"))
    title = _first_string(contexts, ("title",))
    if issue_id is None or title is None:
        return None

    stripped_title = title.strip()
    if not stripped_title or stripped_title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {stripped_title}",
    }


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return likely Linear payload contexts from most to least specific."""

    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)

    trigger_context = event.get("triggerContext")
    data = event.get("data")
    issue = event.get("issue")

    add(trigger_context)
    if isinstance(trigger_context, Mapping):
        add(trigger_context.get("issue"))
        add(trigger_context.get("data"))

    if isinstance(data, Mapping):
        add(data.get("issue"))
    add(data)
    add(issue)
    add(event)
    return contexts


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    trigger_values = []
    for context in contexts:
        for key in ("trigger", "webhookType", "action", "type"):
            value = context.get(key)
            if isinstance(value, str):
                trigger_values.append(_normalize_words(value))

    if any(value in _STATUS_CHANGED_TRIGGERS for value in trigger_values):
        return True

    if not any(value in _ISSUE_UPDATED_TRIGGERS for value in trigger_values):
        return False

    return any(field in _STATUS_FIELD_NAMES for field in _updated_fields(contexts))


def _updated_fields(contexts: list[Mapping[str, Any]]) -> set[str]:
    fields: set[str] = set()
    for context in contexts:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            value = context.get(key)
            if isinstance(value, str):
                fields.add(_normalize_field_name(value))
            elif isinstance(value, list | tuple | set):
                for item in value:
                    if isinstance(item, str):
                        fields.add(_normalize_field_name(item))
    return fields


def _status_name(contexts: list[Mapping[str, Any]]) -> str | None:
    for key in ("newStatus", "new_status", "newState", "new_state"):
        status = _first_string(contexts, (key,))
        if status:
            return status

    for context in contexts:
        for key in ("status", "state", "workflowState", "workflow_state"):
            value = context.get(key)
            if isinstance(value, str):
                return value
            if isinstance(value, Mapping):
                name = value.get("name")
                if isinstance(name, str):
                    return name
    return None


def _first_string(contexts: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _normalize_words(value: str | None) -> str:
    if value is None:
        return ""

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    words = re.sub(r"[^a-zA-Z0-9]+", " ", spaced).strip().lower()
    return re.sub(r"\s+", " ", words)


def _normalize_field_name(value: str) -> str:
    return _normalize_words(value).replace(" ", "")


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
