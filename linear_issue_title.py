"""Helpers for mutating Linear issue titles from status-change events."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any


RESEARCH_STATUS = "to research"
RESEARCH_PREFIX = "Cursor researching"


def _normalize(value: Any) -> str:
    """Normalize user-provided values for stable comparisons."""
    return str(value or "").strip().lower()


def _is_status_changed_to_research(trigger_context: dict[str, Any]) -> bool:
    """Return True when the event is a status change to the research state."""
    return (
        _normalize(trigger_context.get("trigger")) == "status_changed"
        and _normalize(trigger_context.get("newStatus")) == RESEARCH_STATUS
    )


def has_research_prefix(title: str, prefix: str = RESEARCH_PREFIX) -> bool:
    """Check whether the title already begins with the research prefix."""
    escaped_prefix = re.escape(prefix.strip())
    return bool(re.match(rf"^\s*{escaped_prefix}\b", str(title or ""), flags=re.IGNORECASE))


def ensure_research_prefix(title: str, prefix: str = RESEARCH_PREFIX) -> str:
    """Add the research prefix to the title if it is not already present."""
    clean_title = str(title or "").strip()
    if not clean_title:
        return prefix
    if has_research_prefix(clean_title, prefix=prefix):
        return clean_title
    return f"{prefix}: {clean_title}"


@dataclass(frozen=True)
class TitleUpdate:
    """Represents a pending title mutation for a Linear issue."""

    issue_id: str
    previous_title: str
    next_title: str


def build_title_update(event_payload: dict[str, Any] | None) -> TitleUpdate | None:
    """Build a title update when status transitions to 'to research'."""
    trigger_context = (event_payload or {}).get("triggerContext") or {}
    if not _is_status_changed_to_research(trigger_context):
        return None

    current_title = str(trigger_context.get("title") or "")
    next_title = ensure_research_prefix(current_title)

    if next_title == current_title:
        return None

    return TitleUpdate(
        issue_id=str(trigger_context.get("id") or ""),
        previous_title=current_title,
        next_title=next_title,
    )

