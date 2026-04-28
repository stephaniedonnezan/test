"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import re
from typing import Any


TITLE_PREFIX = "Cursor researching"
UPDATE_ACTION = "update_issue_title"
RESEARCH_STATUS = "to_research"
STATUS_CHANGED_TRIGGER = "status_changed"


def build_issue_title_update(event: dict[str, Any]) -> dict[str, str] | None:
    """Return a Linear issue title update when an issue moves to research."""
    context = _trigger_context(event)

    if _normalize(context.get("trigger")) != STATUS_CHANGED_TRIGGER:
        return None

    new_status = context.get("newStatus", context.get("status"))
    if _normalize(new_status) != RESEARCH_STATUS:
        return None

    issue_id = _clean_text(context.get("id", context.get("issueId")))
    current_title = _clean_text(context.get("title"))
    if not issue_id or not current_title:
        return None

    if _has_research_prefix(current_title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {current_title}",
    }


def _trigger_context(event: dict[str, Any]) -> dict[str, Any]:
    context = event.get("triggerContext")
    if isinstance(context, dict):
        return context
    return event


def _normalize(value: Any) -> str:
    text = _clean_text(value).lower()
    return re.sub(r"[\s-]+", "_", text)


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())
