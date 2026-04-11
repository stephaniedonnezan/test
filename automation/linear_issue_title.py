"""Helpers for updating Linear issue titles based on status changes."""

from __future__ import annotations

from typing import Any, Mapping

RESEARCH_PREFIX = "Cursor researching"


def _starts_with_prefix(title: str) -> bool:
    """Return True when a title is already marked as research work."""
    normalized_title = title.strip().lower()
    return normalized_title.startswith(RESEARCH_PREFIX.lower())


def add_research_prefix(issue_title: str) -> str:
    """Add the Cursor research marker to the issue title once."""
    if _starts_with_prefix(issue_title):
        return issue_title
    return f"{RESEARCH_PREFIX}: {issue_title}"


def update_title_for_status_change(issue_title: str, new_status: str) -> str:
    """
    Update an issue title after a status change.

    Rules:
    - When the new status is "to research", prefix title with "Cursor researching".
    - In all other cases, leave the title unchanged.
    """
    if new_status.strip().lower() == "to research":
        return add_research_prefix(issue_title)
    return issue_title


def update_title_from_linear_event(payload: Mapping[str, Any]) -> str:
    """
    Update title directly from a Linear automation payload.

    The payload is expected to include `triggerContext` with keys:
    - `title`: current issue title
    - `newStatus`: status after transition
    """
    trigger_context = payload.get("triggerContext", {})
    issue_title = str(trigger_context.get("title", ""))
    new_status = str(trigger_context.get("newStatus", ""))
    return update_title_for_status_change(issue_title, new_status)
