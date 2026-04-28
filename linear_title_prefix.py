"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import re
from typing import Any, Mapping


RESEARCH_PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"
STATUS_CHANGED_TRIGGER = "status changed"


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to research."""
    context = _trigger_context(event)
    if _normalize(context.get("trigger")) != STATUS_CHANGED_TRIGGER:
        return None

    new_status = context.get("newStatus", context.get("status"))
    if _normalize(new_status) != RESEARCH_STATUS:
        return None

    issue_id = _string_value(context.get("id")) or _string_value(context.get("issueId"))
    title = _string_value(context.get("title"))
    if not issue_id or not title:
        return None

    stripped_title = title.strip()
    if not stripped_title or _has_research_prefix(stripped_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{RESEARCH_PREFIX}: {stripped_title}",
    }


def _trigger_context(event: Mapping[str, Any]) -> Mapping[str, Any]:
    context = event.get("triggerContext")
    if isinstance(context, Mapping):
        return context
    return event


def _normalize(value: Any) -> str:
    text = _string_value(value)
    text = re.sub(r"[_-]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip().casefold()


def _string_value(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(RESEARCH_PREFIX.casefold())
