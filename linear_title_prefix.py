"""Helpers for adding a Linear issue title prefix when research starts."""

from __future__ import annotations

import re
from typing import Any, Mapping


RESEARCH_PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"
STATUS_CHANGED_TRIGGER = "status changed"


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Build an issue-title update action for Linear status-change webhooks.

    The automation trigger payload can arrive either as the raw
    ``triggerContext`` object or wrapped inside ``{"triggerContext": ...}``.
    """

    context = _trigger_context(event)

    if _normalize(context.get("trigger")) != STATUS_CHANGED_TRIGGER:
        return None

    status = context.get("newStatus", context.get("status"))
    if _normalize(status) != RESEARCH_STATUS:
        return None

    title = _clean_string(context.get("title"))
    if not title or _has_research_prefix(title):
        return None

    issue_id = _clean_string(context.get("id") or context.get("issueId"))
    if not issue_id:
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{RESEARCH_PREFIX}: {title}",
    }


def _trigger_context(event: Mapping[str, Any]) -> Mapping[str, Any]:
    context = event.get("triggerContext")
    if isinstance(context, Mapping):
        return context
    return event


def _normalize(value: Any) -> str:
    text = _clean_string(value).casefold()
    text = re.sub(r"[_-]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _clean_string(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(RESEARCH_PREFIX.casefold())
