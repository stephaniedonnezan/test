"""Helpers for updating Linear issue titles from webhook payloads."""

from __future__ import annotations

import re
from typing import Any, Mapping

RESEARCHING_PREFIX = "Cursor researching"
TO_RESEARCH_STATUS = "to research"

_RESEARCHING_PREFIX_PATTERN = re.compile(
    r"^\s*cursor researching(?:\s*[-:|]\s*|\s+)?",
    re.IGNORECASE,
)


def _normalize_status(value: str | None) -> str:
    """Normalize status labels for case-insensitive comparisons."""
    if not value:
        return ""
    return " ".join(value.split()).strip().lower()


def with_researching_prefix(title: str) -> str:
    """Return title with a single researching prefix."""
    stripped_title = title.strip()
    if not stripped_title:
        return RESEARCHING_PREFIX

    if _RESEARCHING_PREFIX_PATTERN.match(stripped_title):
        return stripped_title

    return f"{RESEARCHING_PREFIX} - {stripped_title}"


def updated_title_for_status_change(payload: Mapping[str, Any]) -> str | None:
    """Return updated title for a Linear status-change payload.

    Returns None when no title update is required.
    """
    status = _normalize_status(payload.get("newStatus") or payload.get("status"))
    if status != TO_RESEARCH_STATUS:
        return None

    current_title = str(payload.get("title", "")).strip()
    next_title = with_researching_prefix(current_title)
    if next_title == current_title:
        return None
    return next_title
