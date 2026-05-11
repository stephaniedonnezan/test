"""Build Linear issue title updates for the research status automation."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
PREFIXED_TITLE = f"{PREFIX}: "
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflowstate",
    "workflowstatus",
    "statusid",
    "stateid",
    "workflowstateid",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update payload when an issue moves to research."""

    if not isinstance(event, Mapping):
        return None

    payload = _flatten_event(event)
    if not _is_status_change_event(payload):
        return None

    new_status = _extract_status(payload)
    if _normalize_text(new_status) != _normalize_text(TARGET_STATUS):
        return None

    issue_id = _extract_string(payload, ("id", "issueId", "issue_id", "identifier"))
    title = _extract_string(payload, ("title", "name"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if not title or _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIXED_TITLE}{title}",
    }


def handle_issue_status_changed(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Compatibility wrapper for snake_case callers."""

    return build_issue_title_update(event)


def handleIssueStatusChanged(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Compatibility wrapper for camelCase callers."""

    return build_issue_title_update(event)


def _flatten_event(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common nested Linear payload objects with outer metadata winning."""

    flattened: dict[str, Any] = {}
    for key in ("triggerContext", "data", "issue"):
        value = event.get(key)
        if isinstance(value, Mapping):
            flattened.update(_flatten_event(value))

    flattened.update(event)
    return flattened


def _is_status_change_event(payload: Mapping[str, Any]) -> bool:
    trigger_values = (
        payload.get("trigger"),
        payload.get("webhookType"),
        payload.get("action"),
        payload.get("type"),
    )
    normalized_triggers = {_normalize_text(value) for value in trigger_values if value}

    if "status changed" in normalized_triggers or "statuschanged" in normalized_triggers:
        return True

    issue_update_triggers = {
        "issue updated",
        "updated issue",
        "update issue",
        "issue update",
        "issueupdated",
    }
    if normalized_triggers.intersection(issue_update_triggers):
        return _updated_fields_include_status(payload.get("updatedFields")) or _updated_fields_include_status(
            payload.get("updated_fields")
        )

    return False


def _updated_fields_include_status(updated_fields: Any) -> bool:
    if isinstance(updated_fields, str):
        candidates = [updated_fields]
    elif isinstance(updated_fields, Mapping):
        candidates = list(updated_fields.keys())
    elif isinstance(updated_fields, list | tuple | set):
        candidates = list(updated_fields)
    else:
        return False

    for field in candidates:
        name = field.get("name") if isinstance(field, Mapping) else field
        if _normalize_field_name(name) in _STATUS_FIELD_NAMES:
            return True

    return False


def _extract_status(payload: Mapping[str, Any]) -> str | None:
    status = _extract_string(payload, ("newStatus", "new_status", "status"))
    if status:
        return status

    for key in ("state", "workflowState", "workflow_state"):
        value = payload.get(key)
        if isinstance(value, Mapping):
            nested_status = _extract_string(value, ("name", "title", "status"))
            if nested_status:
                return nested_status

    return None


def _extract_string(payload: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str):
            return value
        if value is not None and not isinstance(value, Mapping | list | tuple | set):
            return str(value)

    return None


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def _normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value.strip())
    return re.sub(r"[\W_]+", " ", spaced).strip().lower()


def _normalize_field_name(value: Any) -> str:
    return _normalize_text(value).replace(" ", "")
