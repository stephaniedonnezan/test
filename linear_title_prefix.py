"""Build title update actions for Linear issues entering research."""

from __future__ import annotations

import re
from typing import Any, Mapping


RESEARCH_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_CHANGED_TRIGGER = "status changed"


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear issue title update action when an issue moves to research."""
    context = _context(event)

    if _normalize(context.get("trigger")) != STATUS_CHANGED_TRIGGER:
        return None

    status = context.get("newStatus", context.get("status"))
    if _normalize(status) != TARGET_STATUS:
        return None

    issue_id = _text(context.get("id") or context.get("issueId"))
    title = _text(context.get("title")).strip()
    if not issue_id or not title or _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{RESEARCH_PREFIX}: {title}",
    }


def _context(event: Mapping[str, Any]) -> Mapping[str, Any]:
    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        return trigger_context
    return event


def _normalize(value: Any) -> str:
    text = _text(value)
    text = re.sub(r"[^a-z0-9]+", " ", text.lower())
    return " ".join(text.split())


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _has_research_prefix(title: str) -> bool:
    return title.lower().lstrip().startswith(RESEARCH_PREFIX.lower())
