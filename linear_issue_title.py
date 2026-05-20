"""Helpers for updating Linear issue titles from status-change payloads."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any


RESEARCH_STATUS = "to research"
TITLE_PREFIX = "Cursor researching"


def normalize_status(status: str | None) -> str:
    """Normalize a Linear status name for comparisons."""
    return " ".join((status or "").strip().casefold().split())


def title_with_research_prefix(title: str) -> str:
    """Return title prefixed with the Cursor research marker exactly once."""
    title = title.strip()
    if title.casefold().startswith(TITLE_PREFIX.casefold()):
        return title
    if not title:
        return TITLE_PREFIX
    return f"{TITLE_PREFIX}: {title}"


def title_for_status_change(payload: dict[str, Any]) -> str | None:
    """Return the updated title when an issue moves to "to research".

    The helper accepts the Cursor/Linear trigger shape used by automations:

    {
      "webhookType": "issue",
      "trigger": "status_changed",
      "newStatus": "To Research",
      "title": "Original title"
    }

    If the payload does not represent an issue status change into the research
    status, None is returned so callers can skip updating the issue.
    """
    if payload.get("webhookType") != "issue":
        return None
    if payload.get("trigger") != "status_changed":
        return None
    if normalize_status(payload.get("newStatus")) != RESEARCH_STATUS:
        return None

    title = payload.get("title")
    if not isinstance(title, str):
        return None
    return title_with_research_prefix(title)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compute a safe Linear issue title for status-change payloads."
    )
    parser.add_argument(
        "payload",
        nargs="?",
        help="JSON payload. If omitted, JSON is read from stdin.",
    )
    args = parser.parse_args()

    raw_payload = args.payload if args.payload is not None else sys.stdin.read()
    payload = json.loads(raw_payload)
    updated_title = title_for_status_change(payload)
    if updated_title is None:
        return 0

    print(updated_title)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
