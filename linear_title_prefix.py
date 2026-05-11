"""Helpers for adding a Cursor research marker to Linear issue titles."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any


RESEARCH_STATUS = "to research"
TITLE_PREFIX = "Cursor researching"


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Build a Linear title update action for issues moved to To Research.

    The automation payloads used by Linear can be flat or nested under
    triggerContext/data/issue. This function accepts both shapes and returns a
    small action object for the caller to execute.
    """

    if not isinstance(event, Mapping):
        return None

    payload = _flatten_event(event)
    if not _is_status_change_event(payload):
        return None

    if _normalize_text(_status_from(payload)) != RESEARCH_STATUS:
        return None

    issue_id = _first_string(payload, ("issueId", "issue_id", "id", "identifier"))
    title = _first_string(payload, ("title", "name"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def handle_issue_status_changed(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Compatibility alias for automation entrypoints."""

    return build_issue_title_update(event)


def _flatten_event(event: Mapping[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}

    issue = _mapping_at(event, "data", "issue") or _mapping_at(event, "issue")
    if issue:
        payload.update(issue)

    data = _mapping_at(event, "data")
    if data:
        payload.update(data)
        nested_issue = _mapping_at(data, "issue")
        if nested_issue:
            payload.update(nested_issue)

    trigger_context = _mapping_at(event, "triggerContext")
    if trigger_context:
        payload.update(trigger_context)

    payload.update(event)
    return payload


def _mapping_at(mapping: Mapping[str, Any], *path: str) -> Mapping[str, Any] | None:
    value: Any = mapping
    for key in path:
        if not isinstance(value, Mapping):
            return None
        value = value.get(key)
    return value if isinstance(value, Mapping) else None


def _is_status_change_event(payload: Mapping[str, Any]) -> bool:
    trigger_value = _first_string(payload, ("trigger", "action", "type", "webhookType"))
    normalized_trigger = _normalize_identifier(trigger_value)
    if normalized_trigger in {"statuschanged", "statuschange", "statusupdated"}:
        return True

    if normalized_trigger in {"issueupdated", "updatedissue", "issueupdate"}:
        return _updated_fields_include_status(payload.get("updatedFields"))

    return False


def _updated_fields_include_status(updated_fields: Any) -> bool:
    status_fields = {"status", "state", "workflowstate", "workflowstatus"}
    if isinstance(updated_fields, str):
        return _normalize_identifier(updated_fields) in status_fields

    if isinstance(updated_fields, Mapping):
        return any(_normalize_identifier(field) in status_fields for field in updated_fields)

    if isinstance(updated_fields, Sequence):
        return any(
            isinstance(field, str) and _normalize_identifier(field) in status_fields
            for field in updated_fields
        )

    return False


def _status_from(payload: Mapping[str, Any]) -> str | None:
    direct_status = _first_string(payload, ("newStatus", "new_status", "status"))
    if direct_status:
        return direct_status

    for key in ("state", "workflowState", "workflowStatus"):
        value = payload.get(key)
        if isinstance(value, Mapping):
            status_name = _first_string(value, ("name", "title"))
            if status_name:
                return status_name

    return None


def _first_string(mapping: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    return re.sub(r"[\s_-]+", " ", spaced).strip().lower()


def _normalize_identifier(value: str | None) -> str:
    return _normalize_text(value).replace(" ", "")
