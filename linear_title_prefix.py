"""Helpers for Linear issue title updates on research status changes."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


RESEARCH_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update action for Linear issues moved to To Research.

    The automation payload can arrive with details inside ``triggerContext`` or
    at the top level. This function stays side-effect free so the caller can
    decide how to apply the returned action to Linear.
    """

    if not isinstance(event, Mapping):
        return None

    context = _context_from(event)
    if _normalize_token(context.get("trigger")) != "status changed":
        return None

    status = context.get("newStatus", context.get("status"))
    if _normalize_token(status) != TARGET_STATUS:
        return None

    issue_id = _first_text(context, "id", "issueId")
    title = _first_text(context, "title")
    if not issue_id or not title:
        return None

    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{RESEARCH_PREFIX}: {title}",
    }


def _context_from(event: Mapping[str, Any]) -> Mapping[str, Any]:
    context = event.get("triggerContext")
    return context if isinstance(context, Mapping) else event


def _first_text(mapping: Mapping[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, str):
            stripped = value.strip()
            if stripped:
                return stripped
    return None


def _normalize_token(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = re.sub(r"[\s_-]+", " ", value.strip().lower())
    return normalized or None


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(RESEARCH_PREFIX.lower())
