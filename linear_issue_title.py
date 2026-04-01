"""Helpers for updating Linear issue titles based on status changes."""

from __future__ import annotations

import re
from typing import Any, Mapping

RESEARCHING_MARKER = "Cursor researching"
TO_RESEARCH_STATUS = "to research"


def _normalize_token(value: str) -> str:
    """Normalize labels for case-insensitive comparisons."""
    return re.sub(r"\s+", " ", value.replace("_", " ").replace("-", " ")).strip().lower()


def _extract_context(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    """Accept either root payloads or payloads nested under triggerContext."""
    trigger_context = payload.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        return trigger_context
    return payload


def with_researching_prefix(title: str, marker: str = RESEARCHING_MARKER) -> str:
    """Prefix a title with marker while avoiding duplicates."""
    clean_title = title.strip()
    if _normalize_token(clean_title).startswith(_normalize_token(marker)):
        return clean_title
    if clean_title in {"", "[]"}:
        return marker
    return f"{marker} - {clean_title}"


def updated_title_for_status_change(payload: Mapping[str, Any], marker: str = RESEARCHING_MARKER) -> str | None:
    """Return updated title when issue status moves to 'to research'."""
    context = _extract_context(payload)

    trigger = _normalize_token(str(context.get("trigger", "")))
    if trigger and trigger != "status changed":
        return None

    status = _normalize_token(str(context.get("newStatus", context.get("status", ""))))
    if status != TO_RESEARCH_STATUS:
        return None

    current_title = str(context.get("title", ""))
    next_title = with_researching_prefix(current_title, marker=marker)
    if next_title == current_title.strip():
        return None
    return next_title
