"""Helpers for updating Linear issue titles from status-change events."""

from __future__ import annotations

import json
import sys
from typing import Any


RESEARCH_STATUS = "to research"
RESEARCH_TITLE_MARKER = "Cursor researching"


def normalize_status(status: str | None) -> str:
    """Normalize Linear status names for comparisons."""
    if not status:
        return ""

    normalized = status.replace("-", " ").replace("_", " ").strip().lower()
    return " ".join(normalized.split())


def title_with_research_marker(title: str, new_status: str | None) -> str:
    """Add the research marker when a Linear issue moves to To Research."""
    if normalize_status(new_status) != RESEARCH_STATUS:
        return title

    if RESEARCH_TITLE_MARKER.lower() in title.lower():
        return title

    return f"{RESEARCH_TITLE_MARKER}: {title}"


def build_title_update(trigger_context: dict[str, Any]) -> dict[str, str] | None:
    """Return a title update payload for matching Linear status-change events."""
    if trigger_context.get("triggerType") != "linear":
        return None

    if trigger_context.get("webhookType") != "issue":
        return None

    if trigger_context.get("trigger") != "status_changed":
        return None

    title = trigger_context.get("title")
    if not isinstance(title, str):
        return None

    new_title = title_with_research_marker(title, trigger_context.get("newStatus"))
    if new_title == title:
        return None

    issue_id = trigger_context.get("id")
    if not isinstance(issue_id, str) or not issue_id:
        return None

    return {"id": issue_id, "title": new_title}


def main() -> int:
    """Read trigger context JSON from stdin and print the needed title update."""
    try:
        trigger_context = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    if not isinstance(trigger_context, dict):
        print("Expected a JSON object", file=sys.stderr)
        return 1

    update = build_title_update(trigger_context)
    if update is None:
        return 0

    print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
