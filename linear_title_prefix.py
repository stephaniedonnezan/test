"""Build Linear issue title update actions for research status changes."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TITLE_PREFIX_WITH_SEPARATOR = f"{TITLE_PREFIX}: "
UPDATE_ISSUE_TITLE_ACTION = "update_issue_title"


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to To Research.

    The Cursor automation trigger provides issue fields inside
    ``triggerContext``. Tests and local callers can also pass the same fields at
    the top level.
    """

    if not isinstance(event, Mapping):
        return None

    context = _event_context(event)
    if _normalize(context.get("trigger")) != "statuschanged":
        return None

    status = context.get("newStatus", context.get("status"))
    if _normalize(status) != "toresearch":
        return None

    issue_id = _string_value(context.get("id", context.get("issueId")))
    title = _string_value(context.get("title"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_research_prefix(title):
        return None

    return {
        "action": UPDATE_ISSUE_TITLE_ACTION,
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX_WITH_SEPARATOR}{title}",
    }


def _event_context(event: Mapping[str, Any]) -> Mapping[str, Any]:
    context = event.get("triggerContext")
    if isinstance(context, Mapping):
        return context
    return event


def _normalize(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"[^a-z0-9]+", "", str(value).strip().lower())


def _string_value(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    return None


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())
