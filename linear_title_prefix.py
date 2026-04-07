"""Helpers for prefixing Linear issue titles on status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any

RESEARCH_TITLE_PREFIX = "Cursor researching"
RESEARCH_STATUS_NAME = "to research"
PREFIX_PATTERN = re.compile(
    rf"^\s*{re.escape(RESEARCH_TITLE_PREFIX)}(?:\s*[-:]\s*|\s+)?",
    flags=re.IGNORECASE,
)


def _normalize_status(status: str) -> str:
    """Normalize status text for reliable comparisons."""
    return " ".join(status.strip().lower().split())


def _prefix_title(title: str, prefix: str = RESEARCH_TITLE_PREFIX) -> str:
    """Prefix title with `Cursor researching` while avoiding duplicates."""
    if PREFIX_PATTERN.match(title):
        return title

    clean_title = title.strip()
    if not clean_title:
        return prefix
    return f"{prefix}: {clean_title}"


def update_issue_title_for_status(title: str, new_status: str) -> str:
    """Return title with research prefix when status is `to research`."""
    if _normalize_status(new_status) == RESEARCH_STATUS_NAME:
        return _prefix_title(title)
    return title


def _extract_trigger_context(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    trigger_context = payload.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        return trigger_context
    return payload


def derive_updated_title(payload: Mapping[str, Any]) -> str | None:
    """Derive the updated title from an automation payload."""
    trigger_context = _extract_trigger_context(payload)

    title = trigger_context.get("title")
    new_status = trigger_context.get("newStatus")
    if not isinstance(title, str) or not isinstance(new_status, str):
        return None

    updated_title = update_issue_title_for_status(title=title, new_status=new_status)
    if updated_title == title:
        return None
    return updated_title


def main() -> int:
    payload = json.load(sys.stdin)
    updated_title = derive_updated_title(payload)
    if updated_title is not None:
        print(updated_title)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
