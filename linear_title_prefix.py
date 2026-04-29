"""Build Linear issue title updates for research status transitions."""

from __future__ import annotations

from collections.abc import Mapping
import re
from typing import Any


CURSOR_RESEARCHING_PREFIX = "Cursor researching"
UPDATE_ISSUE_TITLE_ACTION = "update_issue_title"
RESEARCH_STATUS = "to research"
STATUS_CHANGED_TRIGGER = "status_changed"


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to research."""
    if not isinstance(event, Mapping):
        return None

    context = _trigger_context(event)
    if _normalize_token(context.get("trigger")) != STATUS_CHANGED_TRIGGER:
        return None

    if _normalize_status(context.get("newStatus") or context.get("status")) != RESEARCH_STATUS:
        return None

    issue_id = _string_value(context.get("id") or context.get("issueId"))
    title = _string_value(context.get("title"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_cursor_researching_prefix(title):
        return None

    return {
        "action": UPDATE_ISSUE_TITLE_ACTION,
        "issueId": issue_id,
        "title": f"{CURSOR_RESEARCHING_PREFIX}: {title}",
    }


def _trigger_context(event: Mapping[str, Any]) -> Mapping[str, Any]:
    context = event.get("triggerContext")
    if isinstance(context, Mapping):
        return context
    return event


def _normalize_token(value: Any) -> str:
    text = _string_value(value)
    if not text:
        return ""
    return re.sub(r"[\s-]+", "_", text.strip().lower())


def _normalize_status(value: Any) -> str:
    text = _string_value(value)
    if not text:
        return ""
    return re.sub(r"[\s_-]+", " ", text.strip().lower())


def _string_value(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _has_cursor_researching_prefix(title: str) -> bool:
    return title.lower().startswith(CURSOR_RESEARCHING_PREFIX.lower())
