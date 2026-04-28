"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue title update action for Linear status changes to research."""
    if not isinstance(event, Mapping):
        return None

    context = _event_context(event)
    if _normalize(context.get("trigger")) != "status changed":
        return None

    status = context.get("newStatus", context.get("status"))
    if _normalize(status) != "to research":
        return None

    issue_id = _string_value(context.get("id", context.get("issueId")))
    title = _string_value(context.get("title"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _event_context(event: Mapping[str, Any]) -> Mapping[str, Any]:
    context = event.get("triggerContext")
    if isinstance(context, Mapping):
        return context
    return event


def _normalize(value: Any) -> str:
    text = _string_value(value)
    if not text:
        return ""
    return re.sub(r"[\s_-]+", " ", text).strip().lower()


def _string_value(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())
