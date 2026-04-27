"""Helpers for Linear issue title updates triggered by status changes."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


CURSOR_RESEARCHING_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update action when a Linear issue enters research."""

    if not isinstance(event, Mapping):
        return None

    context = _context(event)
    if _normalize(context.get("trigger")) != "status changed":
        return None

    new_status = context.get("newStatus", context.get("status"))
    if _normalize(new_status) != TARGET_STATUS:
        return None

    title = context.get("title")
    issue_id = context.get("id")
    if not isinstance(title, str) or not title.strip() or not isinstance(issue_id, str):
        return None

    if _has_researching_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{CURSOR_RESEARCHING_PREFIX}: {title}",
    }


def _context(event: Mapping[str, Any]) -> Mapping[str, Any]:
    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        return trigger_context
    return event


def _normalize(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[\s_-]+", " ", value).strip().casefold()


def _has_researching_prefix(title: str) -> bool:
    return title.lstrip().casefold().startswith(CURSOR_RESEARCHING_PREFIX.casefold())
