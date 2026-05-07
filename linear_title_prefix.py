"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_CHANGED_TRIGGER = "status changed"


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to research."""
    if not isinstance(event, Mapping):
        return None

    payload = _flatten_issue_payload(event)
    if not _is_status_changed(payload):
        return None

    status = _first_string(payload, ("newStatus", "new_status", "status"))
    if status is None:
        state = payload.get("state")
        if isinstance(state, Mapping):
            status = _first_string(state, ("name", "status"))

    if _normalize_words(status) != TARGET_STATUS:
        return None

    title = _first_string(payload, ("title", "name"))
    issue_id = _first_string(payload, ("id", "issueId", "issue_id", "identifier"))
    if title is None or issue_id is None:
        return None

    stripped_title = title.strip()
    if not stripped_title or _has_research_prefix(stripped_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {stripped_title}",
    }


def _flatten_issue_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common Linear wrapper fields into one issue-shaped payload."""
    payload: dict[str, Any] = {}

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        payload.update(trigger_context)

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            payload.update(issue)
        payload.update(data)

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        payload.update(issue)

    payload.update(event)
    return payload


def _is_status_changed(payload: Mapping[str, Any]) -> bool:
    trigger = _first_string(payload, ("trigger", "webhookType", "action", "type"))
    return _normalize_words(trigger) == STATUS_CHANGED_TRIGGER


def _first_string(payload: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str):
            return value
    return None


def _normalize_words(value: str | None) -> str | None:
    if value is None:
        return None

    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    normalized = re.sub(r"[^a-zA-Z0-9]+", " ", separated).strip().lower()
    return re.sub(r"\s+", " ", normalized)


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())
