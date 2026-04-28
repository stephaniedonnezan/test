"""Build Linear issue title updates for research-status automations."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


CURSOR_RESEARCHING_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_CHANGED_TRIGGER = "status changed"


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to research.

    The automation trigger may provide issue data either at the top level or
    under ``triggerContext``. Only status-change events moving to "to research"
    should receive the Cursor researching title prefix.
    """

    if not isinstance(event, Mapping):
        return None

    context = _trigger_context(event)
    if _normalize(context.get("trigger")) != STATUS_CHANGED_TRIGGER:
        return None

    new_status = context.get("newStatus", context.get("status"))
    if _normalize(new_status) != TARGET_STATUS:
        return None

    issue_id = context.get("id", context.get("issueId"))
    title = context.get("title")
    if not isinstance(issue_id, str) or not issue_id.strip():
        return None
    if not isinstance(title, str) or not title.strip():
        return None

    cleaned_title = title.strip()
    if _has_cursor_researching_prefix(cleaned_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{CURSOR_RESEARCHING_PREFIX}: {cleaned_title}",
    }


def _trigger_context(event: Mapping[str, Any]) -> Mapping[str, Any]:
    context = event.get("triggerContext")
    if isinstance(context, Mapping):
        return context
    return event


def _normalize(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    normalized = re.sub(r"[\s_-]+", " ", value.strip().lower())
    return normalized


def _has_cursor_researching_prefix(title: str) -> bool:
    return _normalize(title).startswith(CURSOR_RESEARCHING_PREFIX.lower())
