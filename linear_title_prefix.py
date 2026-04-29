"""Helpers for Linear issue title updates triggered by status changes."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
PREFIXED_TITLE_RE = re.compile(r"^\s*cursor researching\b", re.IGNORECASE)


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Build an issue title update action for research-status Linear webhooks.

    The automation payload may pass issue fields directly or under
    ``triggerContext``. Returning ``None`` tells the caller no title update is
    needed for the event.
    """

    if not isinstance(event, Mapping):
        return None

    context = _trigger_context(event)
    if _normalize_token(context.get("trigger")) != "status changed":
        return None

    status = context.get("newStatus", context.get("status"))
    if _normalize_token(status) != "to research":
        return None

    issue_id = _first_string(context, "id", "issueId")
    raw_title = _first_string(context, "title")
    if issue_id is None or raw_title is None:
        return None

    title = raw_title.strip()
    if not title or PREFIXED_TITLE_RE.match(title):
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


def _first_string(source: Mapping[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = source.get(key)
        if isinstance(value, str):
            return value
    return None


def _normalize_token(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()
    return re.sub(r"\s+", " ", normalized)
