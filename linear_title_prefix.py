"""Build Linear issue title updates for Cursor research automation."""

from __future__ import annotations

import re
from typing import Any, Mapping


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_CHANGED_TRIGGER = "status changed"


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update action when an issue moves into research."""
    if not isinstance(event, Mapping):
        return None

    payload = _trigger_context(event)
    if _normalize(payload.get("trigger")) != STATUS_CHANGED_TRIGGER:
        return None

    status = payload.get("newStatus", payload.get("status"))
    if _normalize(status) != TARGET_STATUS:
        return None

    issue_id = _first_text(payload, "id", "issueId")
    title = _first_text(payload, "title")
    if not issue_id or not title:
        return None

    stripped_title = title.strip()
    if _has_research_prefix(stripped_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {stripped_title}",
    }


def _trigger_context(event: Mapping[str, Any]) -> Mapping[str, Any]:
    context = event.get("triggerContext")
    return context if isinstance(context, Mapping) else event


def _first_text(payload: Mapping[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _normalize(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = re.sub(r"[\s_-]+", " ", value.strip().lower())
    return normalized or None


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())
