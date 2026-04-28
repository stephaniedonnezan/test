"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
PREFIXED_TITLE = f"{TITLE_PREFIX}: "
RESEARCH_STATUS = "to research"
STATUS_CHANGED_TRIGGER = "status changed"


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update action when an issue enters research."""
    context = _trigger_context(event)
    if context is None:
        return None

    trigger = _normalize(context.get("trigger"))
    new_status = _normalize(context.get("newStatus") or context.get("status"))
    if trigger != STATUS_CHANGED_TRIGGER or new_status != RESEARCH_STATUS:
        return None

    issue_id = _string_value(context.get("id") or context.get("issueId"))
    title = _string_value(context.get("title"))
    if not issue_id or not title:
        return None

    stripped_title = title.strip()
    if not stripped_title or _already_prefixed(stripped_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIXED_TITLE}{stripped_title}",
    }


def _trigger_context(event: Mapping[str, Any] | None) -> Mapping[str, Any] | None:
    if not isinstance(event, Mapping):
        return None

    context = event.get("triggerContext")
    if isinstance(context, Mapping):
        return context

    return event


def _string_value(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    return None


def _normalize(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    normalized = re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()
    return re.sub(r"\s+", " ", normalized)


def _already_prefixed(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())
