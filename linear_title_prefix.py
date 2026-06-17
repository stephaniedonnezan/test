"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
ACTION = "update_issue_title"
STATUS_FIELDS = {
    "status",
    "state",
    "workflowstate",
    "statusid",
    "stateid",
    "workflowstateid",
}
DIRECT_STATUS_CHANGE_TRIGGERS = {"statuschanged"}
GENERIC_UPDATE_TRIGGERS = {"update", "issueupdated", "updatedissue"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to to research."""
    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_research_status_change(contexts):
        return None

    issue_id = _first_text(contexts, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_text(contexts, ("title", "name"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_prefix(title):
        return None

    return {
        "action": ACTION,
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return nested payload sections from most issue-specific to most general."""
    contexts: list[Mapping[str, Any]] = []

    trigger_context = _mapping(event.get("triggerContext"))
    data = _mapping(event.get("data"))
    issue = _mapping(event.get("issue"))
    data_issue = _mapping(data.get("issue")) if data else None

    for context in (data_issue, issue, data, trigger_context, event):
        if context is not None and context not in contexts:
            contexts.append(context)

    return contexts


def _is_research_status_change(contexts: list[Mapping[str, Any]]) -> bool:
    status = _new_status(contexts)
    if _normalize(status) != "toresearch":
        return False

    if _has_direct_status_trigger(contexts):
        return True

    if _has_generic_update_trigger(contexts):
        return _has_status_field_change(contexts)

    return False


def _new_status(contexts: list[Mapping[str, Any]]) -> str | None:
    status = _first_text(
        contexts,
        (
            "newStatus",
            "new_status",
            "newState",
            "new_state",
            "newWorkflowState",
            "new_workflow_state",
            "status",
        ),
    )
    if status:
        return status

    for key in ("state", "workflowState"):
        nested_status = _first_nested_text(contexts, key, ("name", "title"))
        if nested_status:
            return nested_status

    for change in _changes(contexts):
        if not _is_status_field(change.get("field") or change.get("fieldName") or change.get("key")):
            continue
        next_value = change.get("newValue", change.get("to"))
        text = _value_text(next_value)
        if text:
            return text

    return None


def _has_direct_status_trigger(contexts: list[Mapping[str, Any]]) -> bool:
    return any(
        _normalize(value) in DIRECT_STATUS_CHANGE_TRIGGERS
        for value in _trigger_values(contexts)
    )


def _has_generic_update_trigger(contexts: list[Mapping[str, Any]]) -> bool:
    return any(_normalize(value) in GENERIC_UPDATE_TRIGGERS for value in _trigger_values(contexts))


def _trigger_values(contexts: list[Mapping[str, Any]]) -> list[Any]:
    values: list[Any] = []
    for context in contexts:
        for key in ("trigger", "webhookType", "action", "type"):
            if key in context:
                values.append(context[key])
    return values


def _has_status_field_change(contexts: list[Mapping[str, Any]]) -> bool:
    for key in ("updatedFields", "changedFields"):
        for field in _list_values(contexts, key):
            if _is_status_field(field):
                return True

    return any(
        _is_status_field(change.get("field") or change.get("fieldName") or change.get("key"))
        for change in _changes(contexts)
    )


def _changes(contexts: list[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    changes: list[Mapping[str, Any]] = []
    for key in ("changes", "changed"):
        for value in _list_values(contexts, key):
            if isinstance(value, Mapping):
                changes.append(value)
    return changes


def _first_text(contexts: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        for context in contexts:
            text = _value_text(context.get(key))
            if text:
                return text
    return None


def _first_nested_text(
    contexts: list[Mapping[str, Any]], key: str, nested_keys: tuple[str, ...]
) -> str | None:
    for context in contexts:
        nested = _mapping(context.get(key))
        if nested is None:
            continue
        text = _first_text([nested], nested_keys)
        if text:
            return text
    return None


def _list_values(contexts: list[Mapping[str, Any]], key: str) -> list[Any]:
    values: list[Any] = []
    for context in contexts:
        value = context.get(key)
        if isinstance(value, (list, tuple, set)):
            values.extend(value)
        elif value is not None:
            values.append(value)
    return values


def _mapping(value: Any) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None


def _value_text(value: Any) -> str | None:
    if isinstance(value, str):
        text = value.strip()
        return text or None
    if isinstance(value, Mapping):
        for key in ("name", "title", "identifier", "key", "id"):
            text = _value_text(value.get(key))
            if text:
                return text
    return None


def _is_status_field(field: Any) -> bool:
    text = _value_text(field)
    return bool(text and _normalize(text) in STATUS_FIELDS)


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def _normalize(value: Any) -> str:
    text = _value_text(value)
    if not text:
        return ""
    return re.sub(r"[^a-z0-9]", "", text.lower())


def main() -> int:
    """Read a JSON event from stdin and print an update action when needed."""
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
