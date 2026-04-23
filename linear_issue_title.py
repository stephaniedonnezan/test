"""Utilities to enforce Linear issue-title conventions for status changes."""

from __future__ import annotations

import json
import sys
from typing import Any, Mapping

RESEARCH_STATUS = "to research"
RESEARCH_PREFIX = "Cursor researching"


def _normalize_whitespace(value: str) -> str:
    return " ".join(value.split())


def normalize_status(status: str | None) -> str:
    """Normalize status values for case/whitespace-insensitive matching."""
    if status is None:
        return ""
    return _normalize_whitespace(status.strip().lower())


def status_is_to_research(status: str | None) -> bool:
    """Return True when status matches the to-research state."""
    return normalize_status(status) == RESEARCH_STATUS


def has_prefix(title: str, prefix: str = RESEARCH_PREFIX) -> bool:
    """Return True when the title already starts with the research prefix."""
    return title.strip().lower().startswith(prefix.lower())


def add_research_prefix(title: str, prefix: str = RESEARCH_PREFIX) -> str:
    """Add a single research prefix to title while keeping idempotency."""
    cleaned_title = title.strip()
    if not cleaned_title:
        return prefix
    if has_prefix(cleaned_title, prefix):
        return cleaned_title
    return f"{prefix}: {cleaned_title}"


def build_title_update(
    *,
    title: str,
    new_status: str | None,
    prefix: str = RESEARCH_PREFIX,
) -> str | None:
    """
    Return updated title when the issue enters "to research", else None.

    Returning None allows callers to skip unnecessary API updates.
    """
    if not status_is_to_research(new_status):
        return None
    updated_title = add_research_prefix(title, prefix)
    if updated_title == title:
        return None
    return updated_title


def build_title_update_from_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """
    Build a deterministic action payload from Linear webhook JSON.

    Expected payload shapes:
    - {"triggerContext": {"title": "...", "newStatus": "..."}}
    - {"title": "...", "newStatus": "..."} (fallback)
    """
    context = payload.get("triggerContext", payload)
    title = str(context.get("title", "")).strip()
    new_status = context.get("newStatus", context.get("status"))
    issue_id = context.get("id")

    updated_title = build_title_update(title=title, new_status=new_status)
    return {
        "issue_id": issue_id,
        "should_update": updated_title is not None,
        "new_title": updated_title if updated_title is not None else title,
    }


def main() -> int:
    """Read webhook JSON from stdin and print action JSON to stdout."""
    payload = json.load(sys.stdin)
    result = build_title_update_from_payload(payload)
    json.dump(result, sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
