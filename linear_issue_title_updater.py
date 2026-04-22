"""Utilities to update Linear issue titles for research status transitions."""

from __future__ import annotations

import re
from typing import Any, Dict, Mapping, Optional

RESEARCH_PREFIX = "Cursor researching"
RESEARCHING_PREFIX = RESEARCH_PREFIX
TO_RESEARCH_STATUS = "to research"

_RESEARCH_PREFIX_PATTERN = re.compile(
    r"^\s*cursor researching(?:\s*[-:|]\s*|\s+)?",
    re.IGNORECASE,
)


def _normalize_status(value: Any) -> str:
    """Normalize a status value for case-insensitive comparisons."""
    if not isinstance(value, str):
        return ""
    return " ".join(value.strip().lower().split())


def _extract_trigger_context(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    """Return trigger context from automation payload or raw trigger payload."""
    context = payload.get("triggerContext")
    if isinstance(context, Mapping):
        return context
    return payload


def with_researching_prefix(title: str, prefix: str = RESEARCH_PREFIX) -> str:
    """Return title with a single researching prefix."""
    stripped_title = title.strip()
    if not stripped_title:
        return prefix

    if _RESEARCH_PREFIX_PATTERN.match(stripped_title):
        return stripped_title

    return f"{prefix} - {stripped_title}"


def ensure_prefix(title: str, prefix: str = RESEARCH_PREFIX) -> str:
    """Compatibility wrapper for prior helper naming."""
    return with_researching_prefix(title=title, prefix=prefix)


def updated_title_for_status_change(payload: Mapping[str, Any]) -> Optional[str]:
    """Return updated title for a to-research status transition."""
    context = _extract_trigger_context(payload)

    trigger = context.get("trigger")
    if trigger is not None and trigger != "status_changed":
        return None

    new_status = _normalize_status(context.get("newStatus") or context.get("status"))
    if new_status != TO_RESEARCH_STATUS:
        return None

    title = context.get("title")
    if not isinstance(title, str) or not title.strip():
        return None

    current_title = title.strip()
    next_title = with_researching_prefix(current_title)
    if next_title == current_title:
        return None
    return next_title


def update_issue_title_on_status_change(
    event_payload: Mapping[str, Any],
) -> Optional[Dict[str, str]]:
    """Return a title update instruction when issue moved to 'to research'."""
    context = _extract_trigger_context(event_payload)
    issue_id = context.get("id") or context.get("issueId")
    if not isinstance(issue_id, str) or not issue_id.strip():
        return None

    title = context.get("title")
    if not isinstance(title, str) or not title.strip():
        return None

    new_title = updated_title_for_status_change(context)
    if new_title is None:
        return None

    return {
        "issueId": issue_id.strip(),
        "oldTitle": title.strip(),
        "newTitle": new_title,
    }
