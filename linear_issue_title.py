"""Helpers for adding a research marker to Linear issue titles."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any

RESEARCH_TITLE_MARKER = "Cursor researching"
RESEARCH_STATUS = "to research"

_TITLE_MARKER_PATTERN = re.compile(
    rf"^\s*{re.escape(RESEARCH_TITLE_MARKER)}(?:\s*[-:]\s*|\s+)?",
    flags=re.IGNORECASE,
)


def _normalize_label(value: str) -> str:
    """Normalize user-facing Linear labels for reliable comparisons."""
    return " ".join(value.replace("-", " ").replace("_", " ").strip().lower().split())


def _trigger_context(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    context = payload.get("triggerContext")
    if isinstance(context, Mapping):
        return context
    return payload


def _is_status_change(context: Mapping[str, Any]) -> bool:
    trigger = context.get("trigger")
    if trigger is None:
        return True
    return isinstance(trigger, str) and _normalize_label(trigger) == "status changed"


def add_research_marker_to_title(title: str) -> str:
    """Add the Cursor research marker to an issue title without duplicating it."""
    if _TITLE_MARKER_PATTERN.match(title):
        return title.strip()

    clean_title = title.strip()
    if not clean_title:
        return RESEARCH_TITLE_MARKER
    return f"{RESEARCH_TITLE_MARKER}: {clean_title}"


def title_for_status_change(payload: Mapping[str, Any]) -> str | None:
    """Return the updated title for a Linear status-change payload, if needed."""
    context = _trigger_context(payload)
    if not _is_status_change(context):
        return None

    new_status = context.get("newStatus", context.get("status"))
    title = context.get("title")
    if not isinstance(new_status, str) or not isinstance(title, str):
        return None

    if _normalize_label(new_status) != RESEARCH_STATUS:
        return None

    updated_title = add_research_marker_to_title(title)
    if updated_title == title:
        return None
    return updated_title


def main() -> int:
    payload = json.load(sys.stdin)
    updated_title = title_for_status_change(payload)
    if updated_title is not None:
        print(updated_title)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
