"""Helpers for mutating Linear issue titles on status changes."""

from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any


RESEARCH_PREFIX = "Cursor researching"


def _normalize_status(status: str | None) -> str:
    """Normalize status values to make matching resilient."""
    if not status:
        return ""
    return re.sub(r"[\s_-]+", " ", status.strip().lower())


def add_research_prefix(title: str) -> str:
    """Prepend the research marker to a title when missing."""
    if not title:
        return RESEARCH_PREFIX

    if title.lower().startswith(RESEARCH_PREFIX.lower()):
        return title
    return f"{RESEARCH_PREFIX} {title}"


def updated_title_from_status_change(title: str, new_status: str | None) -> str:
    """Return the expected issue title after a status change."""
    if _normalize_status(new_status) == "to research":
        return add_research_prefix(title)
    return title


def updated_title_from_payload(payload: dict[str, Any]) -> str:
    """Compute the updated title from a Linear automation payload."""
    trigger = payload.get("triggerContext", {})
    title = str(trigger.get("title", ""))
    new_status = trigger.get("newStatus")
    return updated_title_from_status_change(title, new_status)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Update Linear issue title when status becomes 'to research'."
    )
    parser.add_argument(
        "--payload",
        help="Path to JSON payload file. If omitted, reads JSON from stdin.",
    )
    args = parser.parse_args()

    try:
        if args.payload:
            with open(args.payload, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
        else:
            payload = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON payload: {exc}", file=sys.stderr)
        return 2

    print(updated_title_from_payload(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
