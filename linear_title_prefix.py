"""Build title updates for Linear issues that move to research."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


CURSOR_RESEARCHING_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_ISSUE_ID_FIELDS = ("issueId", "issue_id", "id", "identifier")
_STATUS_FIELDS = ("newStatus", "new_status", "status")
_TRIGGER_FIELDS = ("trigger", "action", "type", "webhookType")
_UPDATED_FIELDS = ("updatedFields", "updated_fields", "changedFields", "changed_fields")
_STATUS_CHANGE_EVENTS = {
    "status changed",
    "status change",
    "statuschanged",
    "state changed",
    "state change",
    "statechanged",
}
_ISSUE_UPDATED_EVENTS = {"issue updated", "updated issue"}
_STATUS_FIELD_NAMES = {"status", "state", "workflow state", "workflowstate"}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update action for Linear issues moved to "to research".

    The Cursor automation payload may expose Linear fields either at the top
    level, under ``triggerContext``, or inside nested ``issue``/``data`` maps.
    """

    if not isinstance(event, Mapping):
        return None

    payload = _flatten_event(event)
    if not _is_status_change(payload):
        return None

    if _normalized_status(_status_value(payload)) != TARGET_STATUS:
        return None

    issue_title = _clean_string(payload.get("title"))
    issue_id = _clean_string(_first_present(payload, _ISSUE_ID_FIELDS))
    if not issue_title or not issue_id:
        return None

    if issue_title.casefold().startswith(CURSOR_RESEARCHING_PREFIX.casefold()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{CURSOR_RESEARCHING_PREFIX}: {issue_title}",
    }


def handle_issue_status_changed(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Compatibility alias for automation runtimes using a handler-style name."""

    return build_issue_title_update(event)


def _flatten_event(event: Mapping[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}

    def merge(value: Any) -> None:
        if isinstance(value, Mapping):
            payload.update(value)

    for key in ("triggerContext", "data", "issue"):
        merge(event.get(key))

    data = event.get("data")
    if isinstance(data, Mapping):
        merge(data.get("issue"))

    payload.update(event)
    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        payload.update(trigger_context)

    return payload


def _is_status_change(payload: Mapping[str, Any]) -> bool:
    normalized_events = {
        _normalize_phrase(value)
        for value in (_first_present(payload, (field,)) for field in _TRIGGER_FIELDS)
    }
    normalized_events.discard("")

    if normalized_events & _STATUS_CHANGE_EVENTS:
        return True

    if normalized_events & _ISSUE_UPDATED_EVENTS:
        return _updated_fields_include_status(payload)

    return False


def _updated_fields_include_status(payload: Mapping[str, Any]) -> bool:
    updated_fields = _first_present(payload, _UPDATED_FIELDS)
    if isinstance(updated_fields, str):
        values: list[Any] = [updated_fields]
    elif isinstance(updated_fields, Mapping):
        values = list(updated_fields.keys())
    elif isinstance(updated_fields, list | tuple | set | frozenset):
        values = list(updated_fields)
    else:
        return False

    return any(_normalize_phrase(field) in _STATUS_FIELD_NAMES for field in values)


def _normalized_status(value: Any) -> str:
    if isinstance(value, Mapping):
        value = _first_present(value, ("name", "title"))
    return _normalize_phrase(value)


def _status_value(payload: Mapping[str, Any]) -> Any:
    status = _first_present(payload, _STATUS_FIELDS)
    if status is not None:
        return status

    for field in ("state", "workflowState"):
        value = payload.get(field)
        if value is not None:
            return value

    return None


def _first_present(mapping: Mapping[str, Any], fields: tuple[str, ...]) -> Any:
    for field in fields:
        value = mapping.get(field)
        if value is not None:
            return value
    return None


def _clean_string(value: Any) -> str | None:
    if value is None:
        return None

    cleaned = str(value).strip()
    return cleaned or None


def _normalize_phrase(value: Any) -> str:
    cleaned = _clean_string(value)
    if not cleaned:
        return ""

    with_separated_camel_case = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", cleaned)
    words = re.sub(r"[^A-Za-z0-9]+", " ", with_separated_camel_case).casefold().split()
    return " ".join(words)
