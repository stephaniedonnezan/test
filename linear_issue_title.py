"""Utilities to update Linear issue titles from status change events."""

from __future__ import annotations

import json
import sys
from typing import Any

RESEARCH_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"


def _normalize_status(value: str | None) -> str:
    if not value:
        return ""
    normalized = value.strip().lower().replace("_", " ").replace("-", " ")
    return " ".join(normalized.split())


def should_mark_as_research(new_status: str | None) -> bool:
    """Return True if the status indicates research work."""
    return _normalize_status(new_status) == TARGET_STATUS


def add_research_prefix(title: str) -> str:
    """Ensure the issue title contains the research prefix exactly once."""
    if title.lower().startswith(RESEARCH_PREFIX.lower()):
        return title
    return f"{RESEARCH_PREFIX}: {title}"


def update_issue_title_for_status_change(payload: dict[str, Any]) -> tuple[bool, str | None]:
    """Update the title in-place when status changes to 'to research'."""
    trigger_context = payload.get("triggerContext", payload)
    if not isinstance(trigger_context, dict):
        return False, None

    title = trigger_context.get("title")
    new_status = trigger_context.get("newStatus") or trigger_context.get("status")

    if not isinstance(title, str):
        return False, None
    if not should_mark_as_research(new_status):
        return False, title

    updated_title = add_research_prefix(title)
    trigger_context["title"] = updated_title
    return updated_title != title, updated_title


def main() -> int:
    """Read a Linear event payload from stdin and print updated JSON."""
    payload = json.load(sys.stdin)
    update_issue_title_for_status_change(payload)
    json.dump(payload, sys.stdout, ensure_ascii=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
