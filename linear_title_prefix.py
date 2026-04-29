"""Helpers for adding a Cursor research marker to Linear issue titles."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


RESEARCH_TITLE_PREFIX = "Cursor researching"
UPDATE_ISSUE_TITLE_ACTION = "update_issue_title"


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title-update action for Linear issues moved to research.

    Cursor automation payloads may be passed as the whole event or nested under
    ``triggerContext``. This helper accepts both shapes and returns ``None``
    unless the payload is a status change into "to research".
    """

    if not isinstance(event, Mapping):
        return None

    context = event.get("triggerContext")
    if not isinstance(context, Mapping):
        context = event

    if _normalize(context.get("trigger")) != "status changed":
        return None

    status = context.get("newStatus", context.get("status"))
    if _normalize(status) != "to research":
        return None

    issue_id = _clean_text(context.get("id", context.get("issueId")))
    title = _clean_text(context.get("title"))
    if not issue_id or not title:
        return None

    if _has_research_prefix(title):
        return None

    return {
        "action": UPDATE_ISSUE_TITLE_ACTION,
        "issueId": issue_id,
        "title": f"{RESEARCH_TITLE_PREFIX}: {title}",
    }


def _normalize(value: Any) -> str:
    """Normalize webhook enum/string values for tolerant comparisons."""

    if not isinstance(value, str):
        return ""
    return re.sub(r"[\s_-]+", " ", value.strip().lower())


def _clean_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(RESEARCH_TITLE_PREFIX.lower())
