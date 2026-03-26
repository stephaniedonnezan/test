"""Helpers to update Linear issue titles based on status transitions."""

from __future__ import annotations

import json
import sys
from typing import Any

RESEARCH_STATUS = "to research"
RESEARCH_TITLE_PREFIX = "Cursor researching"


def _normalize(value: str | None) -> str:
    """Normalize user-provided text values for comparisons."""
    if value is None:
        return ""
    return " ".join(value.strip().split()).lower()


def _has_prefix(title: str, prefix: str = RESEARCH_TITLE_PREFIX) -> bool:
    """Check whether the title already starts with the configured prefix."""
    normalized_title = title.lstrip().lower()
    normalized_prefix = prefix.strip().lower()
    return (
        normalized_title == normalized_prefix
        or normalized_title.startswith(f"{normalized_prefix} ")
        or normalized_title.startswith(f"[{normalized_prefix}]")
    )


def add_research_prefix(title: str, prefix: str = RESEARCH_TITLE_PREFIX) -> str:
    """Add the research prefix once, preserving existing titles."""
    cleaned_title = title.strip()
    if not cleaned_title:
        return prefix
    if _has_prefix(cleaned_title, prefix=prefix):
        return cleaned_title
    return f"{prefix} {cleaned_title}"


def update_issue_title_for_status_change(
    title: str,
    new_status: str | None,
    *,
    target_status: str = RESEARCH_STATUS,
    prefix: str = RESEARCH_TITLE_PREFIX,
) -> str:
    """Update title when an issue transitions to the target status."""
    if _normalize(new_status) != _normalize(target_status):
        return title
    return add_research_prefix(title, prefix=prefix)


def build_linear_title_update_payload(event: dict[str, Any]) -> dict[str, str] | None:
    """Build the minimal payload needed to update a Linear issue title."""
    context = event.get("triggerContext", event)
    issue_id = context.get("id")
    title = context.get("title")
    new_status = context.get("newStatus", context.get("status"))

    if not issue_id or title is None:
        return None

    updated_title = update_issue_title_for_status_change(title, new_status)
    if updated_title == title:
        return None

    return {"id": issue_id, "title": updated_title}


def main() -> int:
    """Read a webhook payload from stdin and print update payload."""
    event = json.load(sys.stdin)
    payload = build_linear_title_update_payload(event)
    if payload is None:
        print("{}")
    else:
        print(json.dumps(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
