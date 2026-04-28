"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import re
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_CHANGED_TRIGGER = "status changed"


def build_issue_title_update(event: dict[str, Any]) -> dict[str, str] | None:
    """Return an issue title update action for status changes to research.

    The automation trigger payload has appeared in both nested
    ``triggerContext`` form and flat form, so this accepts either shape.
    """

    context = _trigger_context(event)
    if _normalize(context.get("trigger")) != STATUS_CHANGED_TRIGGER:
        return None

    new_status = context.get("newStatus", context.get("status"))
    if _normalize(new_status) != TARGET_STATUS:
        return None

    issue_id = _string_value(context.get("id")) or _string_value(context.get("issueId"))
    title = _string_value(context.get("title"))
    if not issue_id:
        return None

    title = title.strip()
    if not title:
        return None

    if _has_researching_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _trigger_context(event: dict[str, Any]) -> dict[str, Any]:
    context = event.get("triggerContext")
    if isinstance(context, dict):
        return context
    return event


def _normalize(value: Any) -> str:
    value = _string_value(value)
    if not value:
        return ""
    return re.sub(r"[\s_-]+", " ", value.strip().casefold())


def _string_value(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _has_researching_prefix(title: str) -> bool:
    return title.casefold().startswith(TITLE_PREFIX.casefold())
