"""Build Linear issue title updates for research status transitions."""

from __future__ import annotations

import re
from typing import Any, Mapping


RESEARCH_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_CHANGED_TRIGGER = "status changed"


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to research."""

    context = _trigger_context(event)
    if _normalize(context.get("trigger")) != STATUS_CHANGED_TRIGGER:
        return None

    status = context.get("newStatus", context.get("status"))
    if _normalize(status) != TARGET_STATUS:
        return None

    title = _string_value(context.get("title"))
    issue_id = _string_value(context.get("id") or context.get("issueId"))
    if not title or not issue_id or _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{RESEARCH_PREFIX}: {title}",
    }


def _trigger_context(event: Mapping[str, Any]) -> Mapping[str, Any]:
    context = event.get("triggerContext")
    return context if isinstance(context, Mapping) else event


def _normalize(value: Any) -> str:
    text = _string_value(value)
    text = re.sub(r"[_-]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip().casefold()


def _string_value(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _has_research_prefix(title: str) -> bool:
    return title.lstrip().casefold().startswith(RESEARCH_PREFIX.casefold())
