"""Rule for updating Linear issue titles on status changes.

This module adds the "Cursor researching" marker when an issue enters
"to research" status.
"""

from __future__ import annotations

from typing import Any


RESEARCH_PREFIX = "Cursor researching"


def _normalize_text(value: str) -> str:
    """Normalize text for case-insensitive comparisons."""
    return value.strip().casefold()


def title_with_research_prefix(title: str) -> str:
    """Return title prefixed with RESEARCH_PREFIX, without duplicating it."""
    if _normalize_text(title).startswith(_normalize_text(RESEARCH_PREFIX)):
        return title
    return f"{RESEARCH_PREFIX} - {title}"


def should_mark_as_researching(payload: dict[str, Any]) -> bool:
    """Check whether webhook payload indicates a move to 'to research'."""
    trigger_context = payload.get("triggerContext", {}) or {}
    trigger = trigger_context.get("trigger", "")
    new_status = trigger_context.get("newStatus", "")
    return (
        _normalize_text(str(trigger)) == "status_changed"
        and _normalize_text(str(new_status)) == "to research"
    )


def updated_title_from_payload(payload: dict[str, Any]) -> str | None:
    """Return updated title when rule applies, otherwise None."""
    if not should_mark_as_researching(payload):
        return None

    trigger_context = payload.get("triggerContext", {}) or {}
    current_title = trigger_context.get("title", "")
    if not isinstance(current_title, str) or not current_title.strip():
        return None

    return title_with_research_prefix(current_title)
