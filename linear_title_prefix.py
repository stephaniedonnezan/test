"""Helpers for applying Cursor research prefixes to Linear issue titles."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


RESEARCH_STATUS = "to research"
TITLE_PREFIX = "Cursor researching"


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action for issues moved to research.

    The automation trigger payload may expose issue data either at the top
    level or inside `triggerContext`, so this function accepts both shapes.
    """
    if not isinstance(event, Mapping):
        return None

    context = _mapping_value(event.get("triggerContext")) or event
    if _normalize_token(context.get("trigger")) != "status changed":
        return None

    new_status = context.get("newStatus", context.get("status"))
    if _normalize_token(new_status) != RESEARCH_STATUS:
        return None

    issue_id = _first_text(context, "id", "issueId") or _first_text(
        event, "id", "issueId"
    )
    title = _first_text(context, "title") or _first_text(event, "title")
    if issue_id is None or title is None:
        return None

    title = title.strip()
    if not title or _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _mapping_value(value: Any) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None


def _first_text(source: Mapping[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = source.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _normalize_token(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = re.sub(r"[_\-\s]+", " ", value.strip().lower())
    return normalized or None


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())
