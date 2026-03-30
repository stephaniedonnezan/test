"""Linear issue title prefix handling for automation triggers."""

from __future__ import annotations

from typing import Any, Mapping


RESEARCH_STATUS = "to research"
RESEARCH_PREFIX = "Cursor researching"


def _normalize(value: Any) -> str:
    """Normalize nullable text-like values for case-insensitive matching."""
    if value is None:
        return ""
    return str(value).strip().lower()


def should_add_research_prefix(event: Mapping[str, Any]) -> bool:
    """Return True when a Linear issue status_changed event moves to 'to research'."""
    trigger_context = event.get("triggerContext", {})
    trigger_type = _normalize(trigger_context.get("trigger"))
    new_status = _normalize(trigger_context.get("newStatus"))
    return trigger_type == "status_changed" and new_status == RESEARCH_STATUS


def prefixed_title(title: str, prefix: str = RESEARCH_PREFIX) -> str:
    """Return title prefixed with the research label once."""
    normalized_title = title.strip()
    if _normalize(normalized_title).startswith(_normalize(prefix)):
        return normalized_title
    if not normalized_title:
        return prefix
    return f"{prefix}: {normalized_title}"


def updated_issue_title(event: Mapping[str, Any]) -> str | None:
    """Return updated title if the event requires it, otherwise None."""
    if not should_add_research_prefix(event):
        return None

    trigger_context = event.get("triggerContext", {})
    current_title = str(trigger_context.get("title") or "").strip()
    return prefixed_title(current_title)
