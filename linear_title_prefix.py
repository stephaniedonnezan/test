"""Linear automation for prepending a research title prefix."""

from __future__ import annotations

import re
from typing import Any

PREFIX = "Cursor researching"
_SEPARATOR_PATTERN = re.compile(r"[\s_-]+")
_PREFIX_PATTERN = re.compile(r"^\s*cursor[\s_-]+researching(?:\b|:)", re.IGNORECASE)


def _normalize(value: Any) -> str:
    """Normalize textual trigger/status values for robust comparisons."""
    if not isinstance(value, str):
        return ""
    cleaned = _SEPARATOR_PATTERN.sub(" ", value.strip().lower())
    return re.sub(r"\s+", " ", cleaned).strip()


def _is_status_change_trigger(value: Any) -> bool:
    return _normalize(value) == "status changed"


def _is_to_research_status(value: Any) -> bool:
    return _normalize(value) == "to research"


def _has_prefix(title: str) -> bool:
    return bool(_PREFIX_PATTERN.match(title))


def handle_issue_status_changed(event: dict[str, Any] | None) -> dict[str, str] | None:
    """Return issue-title update payload when issue transitions to 'to research'."""
    if not isinstance(event, dict):
        return None

    trigger_context = event.get("triggerContext")
    if not isinstance(trigger_context, dict):
        return None

    if not _is_status_change_trigger(trigger_context.get("trigger")):
        return None

    new_status = trigger_context.get("newStatus") or trigger_context.get("status")
    if not _is_to_research_status(new_status):
        return None

    issue_id = trigger_context.get("id")
    title = trigger_context.get("title")
    if not isinstance(issue_id, str) or not issue_id.strip():
        return None
    if not isinstance(title, str) or not title.strip():
        return None

    clean_title = title.strip()
    if _has_prefix(clean_title):
        return None
    next_title = f"{PREFIX}: {clean_title}"
    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": next_title,
    }
