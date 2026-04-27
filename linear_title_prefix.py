"""Helpers for Linear issue title updates triggered by status changes."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Mapping
from typing import Any


CURSOR_RESEARCHING_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_CHANGED_TRIGGER = "status changed"
PREFIX_PATTERN = re.compile(
    rf"^\s*{re.escape(CURSOR_RESEARCHING_PREFIX)}(?:\s*[-:]\s*|\s+)?",
    flags=re.IGNORECASE,
)


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Build an issue-title update when a Linear issue enters research."""
    if not isinstance(event, Mapping):
        return None

    context = _context(event)
    if _normalize_token(context.get("trigger")) != STATUS_CHANGED_TRIGGER:
        return None

    new_status = context.get("newStatus", context.get("status"))
    if _normalize_token(new_status) != TARGET_STATUS:
        return None

    title = context.get("title")
    issue_id = context.get("id")
    if not isinstance(title, str) or not title.strip() or not isinstance(issue_id, str):
        return None

    updated_title = add_researching_prefix(title)
    if updated_title == title:
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": updated_title,
    }


def derive_updated_title(event: Mapping[str, Any] | None) -> str | None:
    """Return the updated title for matching payloads, otherwise ``None``."""
    update = build_issue_title_update(event)
    if update is None:
        return None
    return update["title"]


def add_researching_prefix(title: str) -> str:
    """Prefix a title with ``Cursor researching`` without duplicating it."""
    if PREFIX_PATTERN.match(title):
        return title
    return f"{CURSOR_RESEARCHING_PREFIX}: {title.strip()}"


def _context(event: Mapping[str, Any]) -> Mapping[str, Any]:
    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        return trigger_context
    return event


def _normalize_token(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[\s_-]+", " ", value).strip().casefold()


def _load_payload(input_path: str | None) -> Mapping[str, Any]:
    if input_path:
        with open(input_path, encoding="utf-8") as input_file:
            payload = json.load(input_file)
    else:
        payload = json.load(sys.stdin)

    if not isinstance(payload, Mapping):
        raise ValueError("Input payload must be a JSON object.")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Prefix Linear issue titles when status changes to to research.",
    )
    parser.add_argument(
        "--input",
        help="Path to input JSON payload. Reads from stdin when omitted.",
    )
    args = parser.parse_args(argv)

    payload = _load_payload(args.input)
    print(json.dumps({"updatedTitle": derive_updated_title(payload)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
