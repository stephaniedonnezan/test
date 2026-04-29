"""Build title update actions for Linear issues entering research."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to research."""
    if not isinstance(event, Mapping):
        return None

    payload = _issue_payload(event)
    if not _is_status_changed(event, payload):
        return None

    if _normalize_status(_first_text(event, payload, ("newStatus", "new_status", "status"))) != "to research":
        state = payload.get("state")
        if not isinstance(state, Mapping) or _normalize_status(state.get("name")) != "to research":
            return None

    issue_id = _first_text(event, payload, ("id", "issueId", "issue_id", "identifier"))
    title = _first_text(event, payload, ("title",))
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _issue_payload(event: Mapping[str, Any]) -> Mapping[str, Any]:
    for key in ("issue", "data", "triggerContext"):
        value = event.get(key)
        if isinstance(value, Mapping):
            nested = _issue_payload(value)
            if nested:
                return {**nested, **event}
            return {**value, **event}
    return event


def _is_status_changed(event: Mapping[str, Any], payload: Mapping[str, Any]) -> bool:
    value = _first_text(event, payload, ("trigger", "action", "type", "webhookType"))
    return _normalize_token(value) == "statuschanged"


def _first_text(event: Mapping[str, Any], payload: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for source in (event, payload):
        for key in keys:
            value = source.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _normalize_status(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return re.sub(r"[\s_-]+", " ", value.strip().lower())


def _normalize_token(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())
