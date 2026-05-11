"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any


RESEARCH_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"

_STATUS_UPDATE_FIELDS = {"status", "state", "workflowstate", "workflow_state"}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update action when an issue moves to "to research"."""
    if not isinstance(event, Mapping):
        return None

    context = _event_context(event)
    if not _is_status_change_event(context):
        return None

    status = _extract_status(context)
    if _normalize_text(status) != _normalize_text(TARGET_STATUS):
        return None

    title = _clean_string(_first_value(context, ("title", "name")))
    issue_id = _clean_string(
        _first_value(context, ("id", "issueId", "issue_id", "identifier"))
    )
    if not title or not issue_id:
        return None

    if _title_has_research_prefix(title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id,
        "title": f"{RESEARCH_PREFIX}: {title}",
    }


def _event_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten common automation and Linear webhook payload shapes."""
    context: dict[str, Any] = {}

    issue = _mapping_at(event, "issue")
    data = _mapping_at(event, "data")
    trigger_context = _mapping_at(event, "triggerContext")

    if data:
        data_issue = _mapping_at(data, "issue")
        if data_issue:
            context.update(data_issue)
        context.update(data)

    if issue:
        context.update(issue)

    if trigger_context:
        trigger_issue = _mapping_at(trigger_context, "issue")
        trigger_data = _mapping_at(trigger_context, "data")
        if trigger_data:
            trigger_data_issue = _mapping_at(trigger_data, "issue")
            if trigger_data_issue:
                context.update(trigger_data_issue)
            context.update(trigger_data)
        if trigger_issue:
            context.update(trigger_issue)
        context.update(trigger_context)

    context.update(event)
    return context


def _is_status_change_event(context: Mapping[str, Any]) -> bool:
    trigger = _first_value(context, ("trigger", "webhookType", "action", "type"))
    normalized_trigger = _normalize_text(trigger)

    if normalized_trigger in {
        "statuschanged",
        "statuschange",
        "statechanged",
        "workflowstatechanged",
    }:
        return True

    if normalized_trigger in {"issueupdated", "updatedissue"}:
        return _updated_fields_include_status(context.get("updatedFields"))

    return False


def _updated_fields_include_status(updated_fields: Any) -> bool:
    if isinstance(updated_fields, str):
        fields: Sequence[Any] = re.split(r"[\s,]+", updated_fields)
    elif isinstance(updated_fields, Sequence) and not isinstance(
        updated_fields, (bytes, bytearray, str)
    ):
        fields = updated_fields
    else:
        return False

    for field in fields:
        normalized = _normalize_text(field)
        if normalized in _STATUS_UPDATE_FIELDS:
            return True
    return False


def _extract_status(context: Mapping[str, Any]) -> Any:
    status = _first_value(context, ("newStatus", "new_status", "status"))
    if status is not None:
        return status

    state = _mapping_at(context, "state")
    if state:
        state_name = _first_value(state, ("name", "title"))
        if state_name is not None:
            return state_name

    workflow_state = _mapping_at(context, "workflowState") or _mapping_at(
        context, "workflow_state"
    )
    if workflow_state:
        return _first_value(workflow_state, ("name", "title"))

    return None


def _first_value(mapping: Mapping[str, Any], keys: Sequence[str]) -> Any:
    for key in keys:
        value = mapping.get(key)
        if value is not None:
            return value
    return None


def _mapping_at(mapping: Mapping[str, Any], key: str) -> Mapping[str, Any] | None:
    value = mapping.get(key)
    if isinstance(value, Mapping):
        return value
    return None


def _clean_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    cleaned = value.strip()
    return cleaned or None


def _title_has_research_prefix(title: str) -> bool:
    return title.strip().lower().startswith(RESEARCH_PREFIX.lower())


def _normalize_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    spaced_camel_case = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return re.sub(r"[^a-z0-9]+", "", spaced_camel_case.lower())
