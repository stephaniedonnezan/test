"""Build title updates for Linear issues entering research."""

from __future__ import annotations

from collections.abc import Mapping
import re
from typing import Any


PREFIX = "Cursor researching"
PREFIXED_TITLE = f"{PREFIX}: {{title}}"
RESEARCH_STATUS = "to research"
STATUS_CHANGED_TRIGGER = "status changed"


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear issue title update for status changes to research.

    The automation payload may expose issue fields directly or under
    ``triggerContext``. Returning ``None`` tells callers there is no title work
    to perform for the event.
    """
    if not isinstance(event, Mapping):
        return None

    context = _event_context(event)
    if _normalize(context.get("trigger")) != STATUS_CHANGED_TRIGGER:
        return None

    status = context.get("newStatus", context.get("status"))
    if _normalize(status) != RESEARCH_STATUS:
        return None

    issue_id = _text(context.get("id") or context.get("issueId"))
    title = _text(context.get("title"))
    if not issue_id or not title:
        return None

    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": PREFIXED_TITLE.format(title=title),
    }


def _event_context(event: Mapping[str, Any]) -> Mapping[str, Any]:
    context = event.get("triggerContext")
    if isinstance(context, Mapping):
        return context
    return event


def _normalize(value: Any) -> str:
    text = _text(value)
    text = re.sub(r"[_-]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.casefold()


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())
