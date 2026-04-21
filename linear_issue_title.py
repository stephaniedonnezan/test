"""Helpers for mutating Linear issue titles from status-change events."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


RESEARCH_PREFIX = "Cursor researching"


def _normalize(value: Any) -> str:
    """Normalize user-provided values for stable comparisons."""
    if value is None:
        return ""
    return str(value).strip().lower()


def ensure_research_prefix(title: str, prefix: str = RESEARCH_PREFIX) -> str:
    """Add the research prefix to a title if it is not already present."""
    clean_title = (title or "").strip()
    if _normalize(clean_title).startswith(_normalize(prefix)):
        return clean_title
    if not clean_title:
        return prefix
    return f"{prefix} - {clean_title}"


@dataclass(frozen=True)
class TitleUpdate:
    """Represents an issue title update."""

    title: str


def build_title_update(event_payload: dict[str, Any]) -> TitleUpdate | None:
    """Build a title update for events that enter the 'to research' status."""
    context = event_payload.get("triggerContext", {})
    new_status = _normalize(context.get("newStatus"))
    current_title = context.get("title", "")

    if new_status != "to research":
        return None

    updated_title = ensure_research_prefix(current_title)
    if updated_title == (current_title or "").strip():
        return None
    return TitleUpdate(title=updated_title)
