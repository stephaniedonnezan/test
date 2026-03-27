"""Helpers for updating Linear issue titles based on status changes."""

from __future__ import annotations

from typing import Any, Mapping


RESEARCH_PREFIX = "Cursor researching"


def _normalized(value: Any) -> str:
    """Return a lowercase, trimmed string representation for comparisons."""
    return str(value or "").strip().lower()


def should_mark_researching(event_payload: Mapping[str, Any]) -> bool:
    """Return True when the payload indicates a transition to 'to research'."""
    trigger_context = event_payload.get("triggerContext", {})
    if not isinstance(trigger_context, Mapping):
        return False

    return (
        _normalized(trigger_context.get("trigger")) == "status_changed"
        and _normalized(trigger_context.get("newStatus")) == "to research"
    )


def add_research_prefix(title: str, prefix: str = RESEARCH_PREFIX) -> str:
    """Add the researching prefix once, preserving existing titles."""
    cleaned_title = (title or "").strip()
    if not cleaned_title:
        return prefix

    if _normalized(cleaned_title).startswith(_normalized(prefix)):
        return cleaned_title

    return f"{prefix} - {cleaned_title}"


def updated_issue_title(event_payload: Mapping[str, Any]) -> str | None:
    """
    Return an updated title for applicable research status events.

    Returns None when no update should be applied.
    """
    if not should_mark_researching(event_payload):
        return None

    trigger_context = event_payload.get("triggerContext", {})
    title = str(trigger_context.get("title", ""))
    return add_research_prefix(title)
