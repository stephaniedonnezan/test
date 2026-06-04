"""Helpers for prefixing Linear issue titles on research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any

RESEARCH_STATUS_NAME = "to research"
RESEARCH_TITLE_PREFIX = "Cursor researching"

_PREFIX_PATTERN = re.compile(
    rf"^\s*{re.escape(RESEARCH_TITLE_PREFIX)}(?:\s*[-:]\s*|\s+)?",
    flags=re.IGNORECASE,
)


def _normalize_status(status: str) -> str:
    """Normalize Linear status text for stable comparisons."""
    return " ".join(status.strip().casefold().split())


def add_research_prefix(title: str) -> str:
    """Return title prefixed with 'Cursor researching' without duplicating it."""
    if _PREFIX_PATTERN.match(title):
        return title

    stripped_title = title.strip()
    if not stripped_title:
        return RESEARCH_TITLE_PREFIX

    return f"{RESEARCH_TITLE_PREFIX}: {stripped_title}"


def title_for_status_change(title: str, new_status: str) -> str:
    """Add the research prefix when an issue moves to the 'to research' status."""
    if _normalize_status(new_status) == RESEARCH_STATUS_NAME:
        return add_research_prefix(title)

    return title


def _trigger_context(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    trigger_context = payload.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        return trigger_context

    return payload


def updated_title_from_payload(payload: Mapping[str, Any]) -> str | None:
    """Return the new title for a Cursor automation payload, if one is needed."""
    trigger_context = _trigger_context(payload)
    title = trigger_context.get("title")
    new_status = trigger_context.get("newStatus")

    if not isinstance(title, str) or not isinstance(new_status, str):
        return None

    updated_title = title_for_status_change(title, new_status)
    if updated_title == title:
        return None

    return updated_title


def main() -> int:
    payload = json.load(sys.stdin)
    updated_title = updated_title_from_payload(payload)

    if updated_title is not None:
        print(updated_title)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
