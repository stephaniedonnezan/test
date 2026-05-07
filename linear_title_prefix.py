"""Build title updates for Linear issues entering research."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


RESEARCH_STATUS = "toresearch"
TITLE_PREFIX = "Cursor researching"


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear issue title update action for research status changes."""

    if not isinstance(event, Mapping):
        return None

    payload = _merge_payload(event)
    if not _is_status_change(payload):
        return None

    if _compact_text(_status_value(payload)) != RESEARCH_STATUS:
        return None

    issue_id = _first_text(payload, "id", "issueId", "issue_id", "identifier")
    title = _first_text(payload, "title", "issueTitle", "issue_title")
    if not issue_id or not title:
        return None

    stripped_title = title.strip()
    if stripped_title.lower().startswith(TITLE_PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {stripped_title}",
    }


def _merge_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common Linear wrapper shapes with outer fields taking precedence."""

    merged: dict[str, Any] = {}
    for part in (
        _mapping_at(event, "data", "issue"),
        _mapping_at(event, "issue"),
        _mapping_at(event, "data"),
        _mapping_at(event, "triggerContext"),
        event,
    ):
        if part:
            merged.update(part)
    return merged


def _mapping_at(payload: Mapping[str, Any], *path: str) -> Mapping[str, Any] | None:
    current: Any = payload
    for key in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current if isinstance(current, Mapping) else None


def _is_status_change(payload: Mapping[str, Any]) -> bool:
    for key in ("trigger", "webhookType", "action", "type"):
        value = payload.get(key)
        if _looks_like_status_change(value):
            return True

    if _looks_like_issue_update(payload):
        return _updated_fields_include_status(payload)

    return False


def _looks_like_status_change(value: Any) -> bool:
    normalized = _compact_text(value)
    if not normalized:
        return False

    exact_matches = {
        "statuschange",
        "statuschanged",
        "statechange",
        "statechanged",
        "statusupdate",
        "statusupdated",
        "stateupdate",
        "stateupdated",
    }
    if normalized in exact_matches:
        return True

    return ("status" in normalized or "state" in normalized) and (
        "change" in normalized or "update" in normalized
    )


def _looks_like_issue_update(payload: Mapping[str, Any]) -> bool:
    return any(
        _compact_text(payload.get(key)) in {"issueupdated", "issueupdate", "updated"}
        for key in ("trigger", "webhookType", "action", "type")
    )


def _updated_fields_include_status(payload: Mapping[str, Any]) -> bool:
    updated_fields = payload.get("updatedFields") or payload.get("updated_fields")
    if isinstance(updated_fields, str):
        updated_fields = [updated_fields]
    if not isinstance(updated_fields, (list, tuple, set)):
        return False

    return any(_compact_text(field) in {"status", "state"} for field in updated_fields)


def _status_value(payload: Mapping[str, Any]) -> Any:
    for key in ("newStatus", "new_status", "status"):
        if payload.get(key) is not None:
            return payload[key]

    state = payload.get("state")
    if isinstance(state, Mapping):
        return state.get("name")

    return None


def _first_text(payload: Mapping[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _compact_text(value: Any) -> str:
    if value is None:
        return ""

    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", str(value))
    return re.sub(r"[^a-z0-9]+", "", text.lower())
