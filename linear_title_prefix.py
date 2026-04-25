"""Helpers for prefixing Linear issue titles during research handoff."""

from __future__ import annotations

import re
from typing import Any, Mapping


RESEARCH_STATUS = "to research"
TITLE_PREFIX = "Cursor researching"


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title-update action for issues moved to research.

    The automation event is expected to contain a ``triggerContext`` payload
    from Linear. Non-status changes, status changes to other states, and titles
    already carrying the Cursor research prefix are intentionally ignored.
    """

    trigger_context = _mapping_value(event, "triggerContext") or event

    if _normalize_token(trigger_context.get("trigger")) != "status_changed":
        return None

    new_status = trigger_context.get("newStatus", trigger_context.get("status"))
    if _normalize_status(new_status) != RESEARCH_STATUS:
        return None

    issue_id = _string_value(trigger_context.get("id"))
    title = _string_value(trigger_context.get("title"))
    if issue_id is None or title is None:
        return None

    updated_title = prefix_research_title(title)
    if updated_title == title:
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": updated_title,
    }


def prefix_research_title(title: str) -> str:
    """Prefix a title with Cursor's research marker if it is not present."""

    if has_research_prefix(title):
        return title

    stripped_title = title.strip()
    if not stripped_title:
        return f"{TITLE_PREFIX}:"

    return f"{TITLE_PREFIX}: {stripped_title}"


def has_research_prefix(title: str) -> bool:
    """Return whether the title already starts with the research marker."""

    return re.match(rf"^\s*{re.escape(TITLE_PREFIX)}\b", title, re.IGNORECASE) is not None


def _mapping_value(value: Mapping[str, Any], key: str) -> Mapping[str, Any] | None:
    nested = value.get(key)
    return nested if isinstance(nested, Mapping) else None


def _string_value(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _normalize_token(value: Any) -> str:
    if value is None:
        return ""

    return re.sub(r"[\s-]+", "_", str(value).strip().lower())


def _normalize_status(value: Any) -> str:
    if value is None:
        return ""

    return re.sub(r"[\s_-]+", " ", str(value).strip().lower())
