"""Build Linear issue-title updates for research status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {
    "status",
    "status id",
    "state",
    "state id",
    "workflow state",
    "workflow state id",
    "workflow",
    "workflow id",
}

_STATUS_CHANGE_EVENTS = {
    "status changed",
    "status change",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
}

_ISSUE_UPDATE_EVENTS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to research.

    The automation runtime can provide a flat Cursor ``triggerContext`` payload,
    a direct flat mapping, or a nested Linear-style ``data.issue`` payload. This
    function normalizes those shapes and returns a declarative action for the
    caller to apply.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = list(_payload_contexts(event))
    if not _is_status_change_to_research(contexts):
        return None

    issue_id = _first_text(contexts, "issueId", "issue_id", "id", "identifier", "key")
    title = _first_text(contexts, "title", "name")
    if not issue_id or not title:
        return None

    stripped_title = title.strip()
    if _already_prefixed(stripped_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {stripped_title}",
    }


def _payload_contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield useful nested payload objects, ordered from most to least specific."""

    trigger_context = _mapping_at(event, "triggerContext")
    data = _mapping_at(event, "data")
    data_issue = _mapping_at(data, "issue") if data else None
    issue = _mapping_at(event, "issue")

    for context in (trigger_context, data_issue, issue, data, event):
        if context is not None:
            yield context


def _is_status_change_to_research(contexts: list[Mapping[str, Any]]) -> bool:
    if not _is_status_change_event(contexts):
        return False

    status = _changed_status_value(contexts) or _current_status_value(contexts)
    return _normalize_text(status) == TARGET_STATUS


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    event_markers = {
        _normalize_text(value)
        for context in contexts
        for key in ("trigger", "action", "type", "webhookType", "webhook_type")
        for value in (context.get(key),)
        if value is not None
    }

    if event_markers & _STATUS_CHANGE_EVENTS:
        return True

    if event_markers & _ISSUE_UPDATE_EVENTS:
        return any(_is_status_field(field) for field in _changed_field_names(contexts))

    return False


def _changed_status_value(contexts: list[Mapping[str, Any]]) -> str | None:
    explicit_value = _first_text(
        contexts,
        "newStatus",
        "new_status",
        "statusName",
        "status_name",
        "stateName",
        "state_name",
        "workflowStateName",
        "workflow_state_name",
    )
    if explicit_value:
        return explicit_value

    for context in contexts:
        for key in ("changes", "changedFields", "changed_fields", "updatedFields", "updated_fields"):
            value = context.get(key)
            status = _status_value_from_change(value)
            if status:
                return status

    return None


def _current_status_value(contexts: list[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        status = _value_name(context.get("status"))
        if status:
            return status

        state = _value_name(context.get("state"))
        if state:
            return state

        workflow_state = _value_name(context.get("workflowState")) or _value_name(
            context.get("workflow_state")
        )
        if workflow_state:
            return workflow_state

    return None


def _changed_field_names(contexts: list[Mapping[str, Any]]) -> Iterable[str]:
    for context in contexts:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            yield from _field_names(context.get(key))

        for key in ("changes", "updatedFrom", "updated_from"):
            value = context.get(key)
            if isinstance(value, Mapping):
                yield from (str(field) for field in value.keys())
            else:
                yield from _field_names(value)


def _field_names(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
        return

    if isinstance(value, Mapping):
        for key in ("field", "fieldName", "name", "key", "property"):
            field_name = _value_name(value.get(key))
            if field_name:
                yield field_name
        return

    if isinstance(value, Iterable):
        for item in value:
            yield from _field_names(item)


def _status_value_from_change(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for field, change in value.items():
            if _is_status_field(str(field)):
                status = _new_value_from_change(change)
                if status:
                    return status

        if _is_status_field(_value_name(value.get("field")) or _value_name(value.get("name")) or ""):
            return _new_value_from_change(value)

        return None

    if isinstance(value, str):
        return None

    if isinstance(value, Iterable):
        for item in value:
            status = _status_value_from_change(item)
            if status:
                return status

    return None


def _new_value_from_change(change: Any) -> str | None:
    if isinstance(change, Mapping):
        for key in ("newValue", "new_value", "to", "after", "current", "value", "name"):
            status = _value_name(change.get(key))
            if status:
                return status
        return None

    return _value_name(change)


def _first_text(contexts: Iterable[Mapping[str, Any]], *keys: str) -> str | None:
    for context in contexts:
        for key in keys:
            text = _value_name(context.get(key))
            if text and text.strip():
                return text
    return None


def _value_name(value: Any) -> str | None:
    if isinstance(value, str):
        return value

    if isinstance(value, (int, float)):
        return str(value)

    if isinstance(value, Mapping):
        for key in ("name", "title", "label", "value"):
            text = _value_name(value.get(key))
            if text:
                return text

    return None


def _mapping_at(context: Mapping[str, Any] | None, key: str) -> Mapping[str, Any] | None:
    if not isinstance(context, Mapping):
        return None

    value = context.get(key)
    return value if isinstance(value, Mapping) else None


def _is_status_field(value: str) -> bool:
    return _normalize_text(value) in _STATUS_FIELD_NAMES


def _already_prefixed(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""

    text = str(value).strip()
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.casefold().split())


def main() -> int:
    """Read a JSON event from stdin and print the requested title update."""

    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, indent=2, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
