"""Helpers for mutating Linear issue titles from automation events."""

from __future__ import annotations

from typing import Any


RESEARCH_PREFIX = "Cursor researching"


def _normalize(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def should_prefix_research_title(trigger_context: dict[str, Any]) -> bool:
    """Return True when this is an issue status-change to 'to research'."""
    return (
        _normalize(trigger_context.get("trigger")) == "status_changed"
        and _normalize(trigger_context.get("webhookType")) == "issue"
        and _normalize(trigger_context.get("newStatus")) == "to research"
    )


def prefix_research_title(title: str, prefix: str = RESEARCH_PREFIX) -> str:
    """Prefix an issue title with the research marker once."""
    clean_title = title.strip()
    if not clean_title:
        return prefix
    if clean_title.lower().startswith(prefix.lower()):
        return clean_title
    return f"{prefix} {clean_title}"


def update_issue_title_from_event(event: dict[str, Any]) -> str | None:
    """
    Return an updated title when event matches the 'to research' transition.

    Returns None when no title change should be applied.
    """
    trigger_context = event.get("triggerContext")
    if not isinstance(trigger_context, dict):
        return None

    if not should_prefix_research_title(trigger_context):
        return None

    title = trigger_context.get("title")
    if not isinstance(title, str):
        return None

    return prefix_research_title(title)
