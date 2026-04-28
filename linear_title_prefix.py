"""Build Linear issue title updates for research status transitions."""

from __future__ import annotations

import re
from typing import Any, Mapping


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_CHANGE_TRIGGER = "status changed"


def build_issue_title_update(event: Any) -> dict[str, str] | None:
    """Return a title update action when an issue moves to "to research"."""
    context = _context(event)

    if _normalize(context.get("trigger")) != STATUS_CHANGE_TRIGGER:
        return None

    status = context.get("newStatus") or context.get("status")
    if _normalize(status) != TARGET_STATUS:
        return None

    issue_id = _clean(context.get("id") or context.get("issueId"))
    title = _clean(context.get("title"))
    if not issue_id or not title or _already_prefixed(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _context(event: Mapping[str, Any]) -> Mapping[str, Any]:
    if not isinstance(event, Mapping):
        return {}

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        return trigger_context
    return event


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalize(value: Any) -> str:
    return re.sub(r"[\s_-]+", " ", _clean(value)).casefold()


def _already_prefixed(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())
