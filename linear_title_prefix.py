"""Build Linear issue title updates for Cursor research automation."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_CHANGED_TRIGGER = "status changed"


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return an issue-title update for status changes to the research state."""
    if not isinstance(event, Mapping):
        return None

    context = _trigger_context(event)
    if _normalize(context.get("trigger")) != STATUS_CHANGED_TRIGGER:
        return None

    status = context.get("newStatus", context.get("status"))
    if _normalize(status) != TARGET_STATUS:
        return None

    issue_id = _string_value(context.get("id") or context.get("issueId")).strip()
    title = _string_value(context.get("title")).strip()
    if not issue_id or not title:
        return None

    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
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
    return title.casefold().startswith(TITLE_PREFIX.casefold())
