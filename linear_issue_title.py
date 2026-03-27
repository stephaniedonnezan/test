#!/usr/bin/env python3
"""Helpers for updating Linear issue titles when status changes."""

from __future__ import annotations

import re
from typing import Any, Mapping

RESEARCHING_MARKER = "Cursor researching"
RESEARCHING_PREFIX = RESEARCHING_MARKER
TO_RESEARCH_STATUS = "to research"

_RESEARCHING_PREFIX_PATTERN = re.compile(
    r"^\s*cursor researching(?:\s*[-:|]\s*|\s+)?",
    re.IGNORECASE,
)


def _normalize_token(value: str) -> str:
    """Normalize labels for case-insensitive comparisons."""
    return re.sub(r"\s+", " ", value.replace("_", " ").replace("-", " ")).strip().lower()


def _extract_trigger_context(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    """Support payloads with nested triggerContext or root-level fields."""
    trigger_context = payload.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        return trigger_context
    return payload


def with_researching_prefix(title: str, marker: str = RESEARCHING_MARKER) -> str:
    """Prefix the title with marker while avoiding duplicates."""
    clean_title = title.strip()
    if not clean_title or clean_title == "[]":
        return marker

    if _RESEARCHING_PREFIX_PATTERN.match(clean_title):
        return clean_title

    return f"{marker} - {clean_title}"


def maybe_update_issue_title(payload: Mapping[str, Any], marker: str = RESEARCHING_MARKER) -> str | None:
    """Return updated title when issue status moves to 'to research'."""
    context = _extract_trigger_context(payload)

    trigger = _normalize_token(str(context.get("trigger", "")))
    if trigger and trigger != "status changed":
        return None

    new_status = _normalize_token(str(context.get("newStatus", context.get("status", ""))))
    if new_status != TO_RESEARCH_STATUS:
        return None

    current_title = str(context.get("title", ""))
    return with_researching_prefix(current_title, marker=marker)


def updated_title_for_status_change(payload: Mapping[str, Any]) -> str | None:
    """Return updated title only when a status change requires modification."""
    context = _extract_trigger_context(payload)
    current_title = str(context.get("title", "")).strip()
    updated_title = maybe_update_issue_title(payload, marker=RESEARCHING_PREFIX)
    if updated_title is None or updated_title == current_title:
        return None
    return updated_title
