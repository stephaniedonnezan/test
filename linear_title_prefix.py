"""Build Linear issue title updates for Cursor research automation."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
UPDATE_ACTION = "update_issue_title"


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update when an issue moves to To Research."""

    if not isinstance(event, Mapping):
        return None

    payload = _issue_payload(event)
    if not _is_status_change(event, payload):
        return None

    if _normalized_status(_first_value(event, payload, ("newStatus", "new_status", "status"))) != "to research":
        state = payload.get("state")
        if not isinstance(state, Mapping) or _normalized_status(state.get("name")) != "to research":
            return None

    issue_id = _first_value(event, payload, ("id", "issueId", "issue_id", "identifier"))
    title = _first_value(event, payload, ("title",))
    if not isinstance(issue_id, str) or not issue_id.strip():
        return None
    if not isinstance(title, str) or not title.strip():
        return None

    stripped_title = title.strip()
    if stripped_title.lower().startswith(TITLE_PREFIX.lower()):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {stripped_title}",
    }


def _issue_payload(event: Mapping[str, Any]) -> Mapping[str, Any]:
    for key in ("triggerContext", "data", "issue"):
        value = event.get(key)
        if isinstance(value, Mapping):
            nested = _issue_payload(value)
            merged = dict(nested)
            merged.update(value)
            return merged
    return event


def _is_status_change(event: Mapping[str, Any], payload: Mapping[str, Any]) -> bool:
    trigger = _first_value(event, payload, ("trigger", "webhookType", "action", "type"))
    return _normalized_token(trigger) == "statuschanged"


def _first_value(
    event: Mapping[str, Any],
    payload: Mapping[str, Any],
    keys: tuple[str, ...],
) -> Any:
    for source in (event, payload):
        for key in keys:
            value = source.get(key)
            if value is not None:
                return value
    return None


def _normalized_status(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    token = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    token = re.sub(r"[_\-\s]+", " ", token).strip().lower()
    return token or None


def _normalized_token(value: Any) -> str | None:
    status = _normalized_status(value)
    if status is None:
        return None
    return status.replace(" ", "")
