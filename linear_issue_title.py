"""Utilities for adjusting Linear issue titles from webhook events."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

RESEARCH_STATUS = "to research"
RESEARCH_PREFIX = "Cursor researching"


def should_prefix_title(event: dict[str, Any]) -> bool:
    """Return True when the event represents a Linear issue status change to research."""
    trigger_context = event.get("triggerContext")
    if not isinstance(trigger_context, dict):
        return False

    return (
        trigger_context.get("triggerType") == "linear"
        and trigger_context.get("webhookType") == "issue"
        and trigger_context.get("trigger") == "status_changed"
        and str(trigger_context.get("newStatus", "")).strip().casefold() == RESEARCH_STATUS
    )


def add_research_prefix(title: str, prefix: str = RESEARCH_PREFIX) -> str:
    """Prefix an issue title once with the research marker."""
    clean_title = title.strip()
    if clean_title.casefold().startswith(prefix.casefold()):
        return clean_title
    if not clean_title:
        return prefix
    return f"{prefix} - {clean_title}"


def updated_title_for_event(event: dict[str, Any]) -> str | None:
    """Return the new title if the event should update it; otherwise None."""
    if not should_prefix_title(event):
        return None

    trigger_context = event.get("triggerContext", {})
    title = str(trigger_context.get("title", ""))
    return add_research_prefix(title)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Add the 'Cursor researching' prefix for Linear to-research transitions."
    )
    parser.add_argument(
        "--input",
        help="Path to a JSON payload file. If omitted, reads JSON from stdin.",
    )
    args = parser.parse_args()

    if args.input:
        with open(args.input, encoding="utf-8") as payload_file:
            payload = json.load(payload_file)
    else:
        payload = json.load(sys.stdin)

    updated_title = updated_title_for_event(payload)
    print(json.dumps({"updatedTitle": updated_title}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
