"""Helpers for updating Linear issue titles from status change events."""

from __future__ import annotations

from typing import Any, Mapping

RESEARCH_STATUS = "to research"
RESEARCH_PREFIX = "Cursor researching"


def normalize_status(status: str | None) -> str:
    """Normalize status values for stable comparisons."""
    if not status:
        return ""

    collapsed = status.replace("_", " ").replace("-", " ").strip().lower()
    return " ".join(collapsed.split())


def is_to_research_status(status: str | None) -> bool:
    """Return True when a status should trigger research title tagging."""
    return normalize_status(status) == RESEARCH_STATUS


def add_research_prefix(title: str, prefix: str = RESEARCH_PREFIX) -> str:
    """Add a prefix once, preserving the original title text."""
    clean_title = title.strip()

    if not clean_title:
        return prefix

    if clean_title.lower().startswith(prefix.lower()):
        return clean_title

    return f"{prefix}: {clean_title}"


def updated_issue_title(trigger_context: Mapping[str, Any]) -> str:
    """Return a possibly-updated title for a Linear trigger payload."""
    title = str(trigger_context.get("title") or "").strip()
    status = trigger_context.get("newStatus") or trigger_context.get("status")

    if is_to_research_status(status):
        return add_research_prefix(title)

    return title


def build_linear_title_update(trigger_context: Mapping[str, Any]) -> dict[str, str] | None:
    """
    Build the Linear title update payload when a title change is needed.

    Returns None when no title update is required.
    """
    current_title = str(trigger_context.get("title") or "").strip()
    new_title = updated_issue_title(trigger_context)

    if new_title == current_title:
        return None

    issue_id = str(trigger_context.get("id") or "").strip()
    if not issue_id:
        return None

    return {"id": issue_id, "title": new_title}
