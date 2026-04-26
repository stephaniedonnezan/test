"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import re
from typing import Any, Mapping


CURSOR_RESEARCHING_PREFIX = "Cursor researching"


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue title update when an issue moves to "to research"."""

    context = _trigger_context(event)
    if _normalize(context.get("trigger")) != "status changed":
        return None

    new_status = context.get("newStatus", context.get("status"))
    if _normalize(new_status) != "to research":
        return None

    title = _string_value(context.get("title"))
    issue_id = _string_value(context.get("id") or context.get("issueId"))
    if not title or not issue_id:
        return None

    if not should_prefix_issue_title(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": with_researching_prefix(title),
    }


def should_prefix_issue_title(title: str) -> bool:
    """Return whether a title still needs the Cursor researching prefix."""

    return not title.casefold().startswith(CURSOR_RESEARCHING_PREFIX.casefold())


def with_researching_prefix(title: str) -> str:
    """Return title prefixed with the Cursor researching marker."""

    return f"{CURSOR_RESEARCHING_PREFIX}: {title}"


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

