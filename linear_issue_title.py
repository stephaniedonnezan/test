"""Helpers for updating Linear issue titles based on status changes."""

from __future__ import annotations

import re
from typing import Any, Mapping

RESEARCHING_PREFIX = "Cursor researching"
TO_RESEARCH_STATUS = "to research"


def _normalize_label(value: str | None) -> str:
    """Normalize status/trigger labels for case-insensitive comparisons."""
    if not value:
        return ""
    normalized = value.replace("_", " ").replace("-", " ")
    return re.sub(r"\s+", " ", normalized).strip().lower()


def _extract_context(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    """Support payloads wrapped in triggerContext as well as raw payloads."""
    trigger_context = payload.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        return trigger_context
    return payload


def with_researching_prefix(title: str, prefix: str = RESEARCHING_PREFIX) -> str:
    """Return title prefixed with 'Cursor researching' exactly once."""
    cleaned_title = title.strip()
    normalized_prefix = _normalize_label(prefix)

    if _normalize_label(cleaned_title).startswith(normalized_prefix):
        return cleaned_title
    if not cleaned_title:
        return prefix
    return f"{prefix} - {cleaned_title}"


def updated_title_for_status_change(payload: Mapping[str, Any]) -> str | None:
    """Return updated title only when status changed to 'to research'."""
    context = _extract_context(payload)

    trigger = _normalize_label(str(context.get("trigger", "")))
    if trigger and trigger != "status changed":
        return None

    new_status = _normalize_label(str(context.get("newStatus") or context.get("status") or ""))
    if new_status != TO_RESEARCH_STATUS:
        return None

    current_title = str(context.get("title", ""))
    updated_title = with_researching_prefix(current_title)

    if updated_title == current_title.strip():
        return None
    return updated_title
