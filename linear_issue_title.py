"""Helpers for updating Linear issue titles from webhook payloads."""

from __future__ import annotations

import re
from typing import Any, Mapping

RESEARCHING_PREFIX = "Cursor researching"
TO_RESEARCH_STATUS = "to research"
STATUS_CHANGED_TRIGGER = "status changed"

_RESEARCHING_PREFIX_PATTERN = re.compile(
    r"^\s*cursor researching(?:\s*[-:|]\s*|\s+)?",
    re.IGNORECASE,
)


def _normalize_status(value: str | None) -> str:
    """Normalize status labels for case-insensitive comparisons."""
    if not value:
        return ""
    cleaned = value.replace("_", " ").replace("-", " ")
    return " ".join(cleaned.split()).strip().lower()


def _extract_trigger_context(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    """Support raw payloads and wrapped payloads with triggerContext."""
    trigger_context = payload.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        return trigger_context
    return payload


def with_researching_prefix(title: str) -> str:
    """Return title with a single researching prefix."""
    stripped_title = title.strip()
    if not stripped_title:
        return RESEARCHING_PREFIX

    if _RESEARCHING_PREFIX_PATTERN.match(stripped_title):
        return stripped_title

    return f"{RESEARCHING_PREFIX} - {stripped_title}"


def updated_title_for_status_change(payload: Mapping[str, Any]) -> str | None:
    """Return the updated title for a Linear status-change payload.

    Returns None when no title update is required.
    """
    context = _extract_trigger_context(payload)

    trigger = _normalize_status(str(context.get("trigger", "")))
    if trigger and trigger != STATUS_CHANGED_TRIGGER:
        return None

    status = _normalize_status(str(context.get("newStatus") or context.get("status") or ""))
    if status != TO_RESEARCH_STATUS:
        return None

    current_title = str(context.get("title", "")).strip()
    next_title = with_researching_prefix(current_title)
    if next_title == current_title:
        return None
    return next_title
