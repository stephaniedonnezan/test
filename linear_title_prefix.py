"""Build Linear issue title updates for research status transitions."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
UPDATE_ACTION = "update_issue_title"

_STATUS_CHANGE_TOKENS = {"statuschanged", "statuschange", "statusupdated"}
_STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow_state"}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to research."""

    if not isinstance(event, Mapping):
        return None

    payload = _payload_view(event)
    if not _is_status_change(payload):
        return None

    if _normalize_status(_extract_status(payload)) != "to research":
        return None

    issue_id = _clean_string(_extract_first(payload, ("issueId", "issue_id", "id", "identifier")))
    title = _clean_string(_extract_first(payload, ("title",)))
    if not issue_id or not title:
        return None

    if title.lower().startswith(TITLE_PREFIX.lower()):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


handle_issue_status_changed = build_issue_title_update


def _payload_view(event: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten common Linear automation payload wrappers into one lookup view."""

    view: dict[str, Any] = {}

    def merge(value: Any) -> None:
        if isinstance(value, Mapping):
            view.update(value)

    merge(event.get("issue"))

    data = event.get("data")
    if isinstance(data, Mapping):
        merge(data.get("issue"))
        merge(data)

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        merge(trigger_context.get("issue"))
        merge(trigger_context)

    # Top-level automation metadata should win over nested issue fields.
    merge(event)
    return view


def _is_status_change(payload: Mapping[str, Any]) -> bool:
    for field in ("trigger", "action", "type"):
        if _normalize_token(payload.get(field)) in _STATUS_CHANGE_TOKENS:
            return True

    webhook_type = _normalize_token(payload.get("webhookType"))
    if webhook_type in _STATUS_CHANGE_TOKENS:
        return True

    event_name = _normalize_token(_extract_first(payload, ("trigger", "action", "type")))
    if event_name in {"issueupdated", "updatedissue"}:
        return _updated_fields_include_status(payload.get("updatedFields"))

    return False


def _updated_fields_include_status(updated_fields: Any) -> bool:
    if isinstance(updated_fields, str):
        fields = [updated_fields]
    elif isinstance(updated_fields, Mapping):
        fields = updated_fields.keys()
    elif isinstance(updated_fields, list | tuple | set | frozenset):
        fields = updated_fields
    else:
        return False

    return any(_normalize_token(field) in _STATUS_FIELD_NAMES for field in fields)


def _extract_status(payload: Mapping[str, Any]) -> Any:
    status = _extract_first(payload, ("newStatus", "new_status", "status"))
    if status is not None:
        return status

    for state_field in ("state", "workflowState", "workflow_state"):
        state = payload.get(state_field)
        if isinstance(state, Mapping):
            state_name = _extract_first(state, ("name", "title"))
            if state_name is not None:
                return state_name

    return None


def _extract_first(payload: Mapping[str, Any], fields: tuple[str, ...]) -> Any:
    for field in fields:
        if field in payload:
            return payload[field]
    return None


def _clean_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def _normalize_status(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    normalized = _split_camel_case(value)
    normalized = re.sub(r"[_\-\s]+", " ", normalized).strip().lower()
    return normalized or None


def _normalize_token(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    normalized = _split_camel_case(value)
    normalized = re.sub(r"[^a-zA-Z0-9]+", "", normalized).lower()
    return normalized or None


def _split_camel_case(value: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
