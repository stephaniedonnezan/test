"""Utilities for updating Linear issue titles from automation events.

Rule implemented:
- When an issue status changes to "to research", ensure the issue title
  starts with "Cursor researching".
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any


RESEARCH_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"


def _normalize(value: Any) -> str:
    """Normalize text for tolerant comparisons."""
    if value is None:
        return ""
    return " ".join(str(value).strip().lower().split())


def should_prefix_title(event: dict[str, Any]) -> bool:
    """Return True when event is a status change to 'to research'."""
    trigger_context = event.get("triggerContext", {})
    trigger = _normalize(trigger_context.get("trigger"))
    new_status = _normalize(trigger_context.get("newStatus"))

    return trigger == "status_changed" and new_status == TARGET_STATUS


def with_research_prefix(title: str) -> str:
    """Return title with a single research prefix."""
    cleaned = title.strip()
    if _normalize(cleaned).startswith(_normalize(RESEARCH_PREFIX)):
        return cleaned
    return f"{RESEARCH_PREFIX} {cleaned}"


def apply_title_rule(event: dict[str, Any]) -> dict[str, Any]:
    """Apply title prefixing rule in-place-safe style and return new event."""
    updated = dict(event)
    trigger_context = dict(updated.get("triggerContext", {}))
    title = str(trigger_context.get("title", "")).strip()

    if title and should_prefix_title(updated):
        trigger_context["title"] = with_research_prefix(title)
        updated["triggerContext"] = trigger_context

    return updated


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Apply the 'Cursor researching' title rule when a Linear issue "
            "moves to 'to research'."
        )
    )
    parser.add_argument(
        "--payload-file",
        help="Path to JSON payload file. If omitted, read JSON from stdin.",
    )
    args = parser.parse_args()

    if args.payload_file:
        with open(args.payload_file, "r", encoding="utf-8") as file_obj:
            payload = json.load(file_obj)
    else:
        payload = json.load(sys.stdin)

    updated = apply_title_rule(payload)
    print(json.dumps(updated, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
