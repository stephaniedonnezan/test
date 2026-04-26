"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import re
from typing import Any, Mapping


RESEARCH_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update payload when a Linear issue moves to research."""

    context = _trigger_context(event)
    if _normalize(context.get("trigger") or event.get("trigger")) != "status changed":
        return None

    new_status = context.get("newStatus") or context.get("status") or event.get("newStatus") or event.get("status")
    if _normalize(new_status) != TARGET_STATUS:
        return None

    title = context.get("title") or event.get("title")
    issue_id = context.get("id") or context.get("issueId") or event.get("id") or event.get("issueId")
    if not isinstance(title, str) or not title.strip() or not isinstance(issue_id, str) or not issue_id.strip():
        return None

    if _has_research_prefix(title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id,
        "title": f"{RESEARCH_PREFIX}: {title}",
    }


def _trigger_context(event: Mapping[str, Any]) -> Mapping[str, Any]:
    context = event.get("triggerContext")
    if isinstance(context, Mapping):
        return context
    return {}


def _normalize(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    separated = re.sub(r"[_-]+", " ", value)
    words = re.sub(r"\s+", " ", separated).strip().casefold()
    return words


def _has_research_prefix(title: str) -> bool:
    return title.lstrip().casefold().startswith(RESEARCH_PREFIX.casefold())
