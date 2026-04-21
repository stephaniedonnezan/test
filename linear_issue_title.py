"""Helpers for formatting Linear issue titles from status-change events."""

from __future__ import annotations

import argparse
import json
from typing import Any

RESEARCH_PREFIX = "Cursor researching"
RESEARCH_STATUSES = {"to research"}


def apply_status_title_rule(title: str, new_status: str) -> str:
    """Return an updated issue title according to status-change rules."""
    normalized_status = new_status.strip().lower()
    if normalized_status not in RESEARCH_STATUSES:
        return title

    if title.startswith(RESEARCH_PREFIX):
        return title

    return f"{RESEARCH_PREFIX} - {title}"


def updated_title_from_trigger_payload(payload: dict[str, Any]) -> str:
    """Extract title and status from trigger payload and return updated title."""
    trigger_context = payload.get("triggerContext", {})
    title = trigger_context.get("title", "")
    new_status = trigger_context.get("newStatus", "")
    return apply_status_title_rule(title=title, new_status=new_status)


def main() -> None:
    """Read payload JSON and print the updated issue title."""
    parser = argparse.ArgumentParser(
        description="Apply issue title rules for Linear status changes."
    )
    parser.add_argument(
        "--payload",
        help="Raw JSON payload. If omitted, JSON is read from stdin.",
    )
    args = parser.parse_args()

    raw_payload = args.payload if args.payload is not None else input()
    payload = json.loads(raw_payload)
    print(updated_title_from_trigger_payload(payload))


if __name__ == "__main__":
    main()
