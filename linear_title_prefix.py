"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
UPDATE_ACTION = "update_issue_title"
RESEARCH_STATUS = "to_research"
STATUS_FIELD_NAMES = frozenset({"status", "state", "stateid", "workflowstate"})
STATUS_CHANGED_TRIGGER = "status_changed"


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear issue title update when an issue moves to research."""
    if not isinstance(event, Mapping):
        return None

    context = _event_context(event)
    if not _is_status_change_event(context):
        return None

    if _normalize(_new_status(context)) != RESEARCH_STATUS:
        return None

    issue_id = _clean_text(_first_value(context, "id", "issueId", "issue_id", "identifier"))
    current_title = _clean_text(_first_value(context, "title", "name"))
    if not issue_id or not current_title:
        return None

    if _has_research_prefix(current_title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {current_title}",
    }


def _event_context(event: Mapping[str, Any]) -> dict[str, Any]:
    context: dict[str, Any] = {}

    for source in (
        event.get("data"),
        _mapping_value(event.get("data"), "issue"),
        event.get("issue"),
        event.get("triggerContext"),
        event,
    ):
        if isinstance(source, Mapping):
            context.update(source)

    return context


def _is_status_change_event(context: Mapping[str, Any]) -> bool:
    trigger = _normalize(_first_value(context, "trigger", "webhookType", "action", "type"))
    if trigger == STATUS_CHANGED_TRIGGER:
        return True

    if trigger not in {"issue_updated", "updated_issue", "update"}:
        return False

    return any(_normalize(field) in STATUS_FIELD_NAMES for field in _updated_fields(context))


def _updated_fields(context: Mapping[str, Any]) -> list[Any]:
    fields = _first_value(context, "updatedFields", "updated_fields")
    if isinstance(fields, list | tuple | set):
        return list(fields)

    if isinstance(fields, Mapping):
        return list(fields)

    updated_from = context.get("updatedFrom")
    if isinstance(updated_from, Mapping):
        return list(updated_from)

    return []


def _new_status(context: Mapping[str, Any]) -> Any:
    for key in ("newStatus", "new_status", "status", "state", "workflowState"):
        status = _nested_name(context.get(key))
        if status:
            return status

    return None


def _first_value(context: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        value = context.get(key)
        if value is not None:
            return value
    return None


def _mapping_value(value: Any, key: str) -> Any:
    if isinstance(value, Mapping):
        return value.get(key)
    return None


def _nested_name(value: Any) -> str:
    if isinstance(value, Mapping):
        return _clean_text(value.get("name"))
    return _clean_text(value)


def _normalize(value: Any) -> str:
    text = _clean_text(value)
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", text)
    text = re.sub(r"[^A-Za-z0-9]+", "_", text)
    return text.strip("_").lower()


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())
