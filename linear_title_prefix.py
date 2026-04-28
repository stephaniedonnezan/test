"""Helpers for marking Linear issues as being researched by Cursor."""

from __future__ import annotations

import re
from typing import Any


TITLE_PREFIX = "Cursor researching"


def build_issue_title_update(event: dict[str, Any]) -> dict[str, str] | None:
    """Return an issue title update when a Linear issue moves to To Research.

    The Cursor automation payload currently places Linear issue details under
    ``triggerContext``. Accepting flat payloads as well keeps the helper easy to
    exercise and tolerant of minor webhook-shape differences.
    """

    context = _event_context(event)

    if _normalize_token(context.get("trigger")) != "statuschanged":
        return None

    status = context.get("newStatus", context.get("status"))
    if _normalize_words(status) != "to research":
        return None

    issue_id = _first_text(context, "id", "issueId")
    title = _first_text(context, "title")
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_cursor_researching_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _event_context(event: dict[str, Any]) -> dict[str, Any]:
    context = event.get("triggerContext")
    if isinstance(context, dict):
        return context
    return event


def _first_text(context: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = context.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _normalize_token(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _normalize_words(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _has_cursor_researching_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())
