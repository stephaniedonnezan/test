"""Build Linear issue title updates for research-status automations."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_CHANGE_TRIGGERS = {
    "status changed",
    "status change",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
}
_ISSUE_UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}
_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflowstate",
    "workflow state",
    "state id",
    "stateid",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title-update action when a Linear issue moves to research."""
    if not isinstance(event, Mapping):
        return None

    contexts = _payload_contexts(event)
    if not _is_status_change_event(contexts):
        return None

    status = _status_name(contexts)
    if _normalize_words(status) != TARGET_STATUS:
        return None

    issue_id = _first_string(contexts, ("id", "issueId", "issue_id", "identifier"))
    title = _first_string(contexts, ("title", "name"))
    if issue_id is None or title is None:
        return None

    issue_id = issue_id.strip()
    title = title.strip()
    if not issue_id or not title or _already_prefixed(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _payload_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return likely Linear payload contexts from most to least specific."""
    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)

    add(event.get("triggerContext"))

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        add(trigger_context.get("issue"))
        add(trigger_context.get("data"))

    data = event.get("data")
    if isinstance(data, Mapping):
        add(data.get("issue"))

    add(data)
    add(event.get("issue"))
    add(event)
    return contexts


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    trigger_values = [
        _normalize_words(value)
        for context in contexts
        for key in ("trigger", "event", "eventType", "webhookType", "type", "action")
        if isinstance((value := context.get(key)), str)
    ]

    if any(value in _STATUS_CHANGE_TRIGGERS for value in trigger_values):
        return True

    if not any(value in _ISSUE_UPDATE_TRIGGERS for value in trigger_values):
        return False

    return any(field in _STATUS_FIELD_NAMES for field in _updated_fields(contexts))


def _updated_fields(contexts: list[Mapping[str, Any]]) -> set[str]:
    fields: set[str] = set()
    for context in contexts:
        for key in (
            "updatedFields",
            "updated_fields",
            "changedFields",
            "changed_fields",
        ):
            value = context.get(key)
            if isinstance(value, str):
                fields.add(_normalize_field_name(value))
            elif isinstance(value, Sequence) and not isinstance(value, str):
                fields.update(
                    _normalize_field_name(item) for item in value if isinstance(item, str)
                )

        updated_from = context.get("updatedFrom")
        if isinstance(updated_from, Mapping):
            fields.update(_normalize_field_name(key) for key in updated_from)

    return fields


def _status_name(contexts: list[Mapping[str, Any]]) -> str | None:
    for key in ("newStatus", "new_status", "newState", "new_state", "status"):
        status = _first_string(contexts, (key,))
        if status:
            return status

    for context in contexts:
        for key in ("state", "workflowState", "workflow_state"):
            value = context.get(key)
            if isinstance(value, str):
                return value
            if isinstance(value, Mapping):
                name = value.get("name") or value.get("title")
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


def _already_prefixed(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def _normalize_words(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    value = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    value = re.sub(r"[^a-zA-Z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip().lower()


def _normalize_field_name(value: str) -> str:
    return _normalize_words(value).replace(" ", "")


def main() -> int:
    """Read a JSON payload from stdin and print the requested update, if any."""
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON payload: {exc}", file=sys.stderr)
        return 1

    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
