"""Build Linear issue title updates for research-status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_CAMEL_BOUNDARY_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")

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

_STATUS_FIELD_NAMES = {
    "status",
    "status id",
    "state",
    "state id",
    "workflow state",
    "workflow state id",
}

_TRIGGER_KEYS = ("trigger", "webhookType", "action", "type", "eventType")
_UPDATED_FIELD_KEYS = (
    "updatedFields",
    "updated_fields",
    "changedFields",
    "changed_fields",
)
_CHANGE_KEYS = ("changes", "updatedFrom", "updated_from", "previousValues")
_EXPLICIT_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newStatusName",
    "new_status_name",
    "newState",
    "new_state",
    "newWorkflowState",
    "new_workflow_state",
)
_CURRENT_STATUS_KEYS = ("status", "state", "workflowState", "workflow_state")
_ISSUE_ID_KEYS = ("issueId", "issue_id", "id", "identifier", "key")
_TITLE_KEYS = ("title",)


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue-title update action when an issue moves to To Research.

    The Cursor automation payload is flat inside ``triggerContext``, while
    Linear webhook payloads often nest issue details under ``data`` or
    ``data.issue``. This function accepts both shapes and intentionally returns
    ``None`` for events that are not status changes to the target status.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    if _normalize_status(_new_status(event)) != TARGET_STATUS:
        return None

    issue_id = _first_text(_ISSUE_ID_KEYS, _issue_contexts(event))
    title = _first_text(_TITLE_KEYS, _issue_contexts(event))
    if not issue_id or not title:
        return None

    title = title.strip()
    if not title or _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    event_values = [
        _normalize_token(value)
        for context in _event_contexts(event)
        for key in _TRIGGER_KEYS
        for value in _mapping_values(context, key)
    ]

    if any(value in _DIRECT_STATUS_CHANGE_EVENTS for value in event_values):
        return True

    if any(value in _GENERIC_UPDATE_EVENTS for value in event_values):
        return _updated_fields_include_status(event)

    return False


def _updated_fields_include_status(event: Mapping[str, Any]) -> bool:
    for context in _event_contexts(event):
        for key in _UPDATED_FIELD_KEYS:
            for value in _mapping_values(context, key):
                if _field_collection_includes_status(value):
                    return True

        for key in _CHANGE_KEYS:
            for value in _mapping_values(context, key):
                if isinstance(value, Mapping):
                    if any(_is_status_field(field) for field in value):
                        return True
                elif _field_collection_includes_status(value):
                    return True

    return False


def _new_status(event: Mapping[str, Any]) -> Any:
    contexts = _event_contexts(event)
    for context in contexts:
        for key in _EXPLICIT_STATUS_KEYS:
            for value in _mapping_values(context, key):
                if value not in (None, ""):
                    return value

    for context in contexts:
        for key in _CURRENT_STATUS_KEYS:
            for value in _mapping_values(context, key):
                if value not in (None, ""):
                    return value

    return None


def _issue_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []

    trigger_context = _child_mapping(event, "triggerContext")
    data = _child_mapping(event, "data")
    issue = _child_mapping(data, "issue") or _child_mapping(event, "issue")
    node = _child_mapping(data, "node")

    for context in (trigger_context, issue, node, data, event):
        if context and context not in contexts:
            contexts.append(context)

    return contexts


def _event_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []
    data = _child_mapping(event, "data")
    issue = _child_mapping(data, "issue") if data else None
    node = _child_mapping(data, "node") if data else None

    for context in (
        event,
        _child_mapping(event, "triggerContext"),
        data,
        issue,
        node,
        _child_mapping(event, "issue"),
    ):
        if context and context not in contexts:
            contexts.append(context)

    return contexts


def _child_mapping(parent: Mapping[str, Any] | None, key: str) -> Mapping[str, Any] | None:
    if not isinstance(parent, Mapping):
        return None

    child = parent.get(key)
    return child if isinstance(child, Mapping) else None


def _mapping_values(context: Mapping[str, Any], key: str) -> Iterable[Any]:
    if key in context:
        yield context[key]


def _first_text(keys: Iterable[str], contexts: Iterable[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value
            if isinstance(value, int):
                return str(value)

    return None


def _field_collection_includes_status(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)

    if isinstance(value, Mapping):
        return any(_is_status_field(field) for field in value)

    if isinstance(value, Iterable):
        return any(_field_collection_includes_status(item) for item in value)

    return False


def _is_status_field(value: Any) -> bool:
    return _normalize_token(value) in _STATUS_FIELD_NAMES


def _normalize_status(value: Any) -> str:
    if isinstance(value, Mapping):
        for key in ("name", "label", "title"):
            nested_value = value.get(key)
            if isinstance(nested_value, str):
                value = nested_value
                break

    return _normalize_token(value)


def _normalize_token(value: Any) -> str:
    if value is None:
        return ""

    token = _CAMEL_BOUNDARY_RE.sub(" ", str(value))
    token = _NON_ALNUM_RE.sub(" ", token.lower())
    return " ".join(token.split())


def _has_prefix(title: str) -> bool:
    return title.lstrip().lower().startswith(PREFIX.lower())


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 2

    update = build_issue_title_update(event)
    if update is None:
        return 1

    print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
