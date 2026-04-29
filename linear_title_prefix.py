"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_CHANGED_TRIGGER = "status changed"


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return an issue title update action when a Linear issue enters research."""
    if not isinstance(event, Mapping):
        return None

    context = _trigger_context(event)
    if _normalize(context.get("trigger")) != STATUS_CHANGED_TRIGGER:
        return None

    status = context.get("newStatus", context.get("status"))
    if _normalize(status) != TARGET_STATUS:
        return None

    issue_id = _text_value(context.get("id")) or _text_value(context.get("issueId"))
    title = _text_value(context.get("title"))
    if not issue_id or not title:
        return None

    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _trigger_context(event: Mapping[str, Any]) -> Mapping[str, Any]:
    context = event.get("triggerContext")
    if isinstance(context, Mapping):
        return context
    return event


def _normalize(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[\s_-]+", " ", value.strip().casefold())


def _text_value(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())
