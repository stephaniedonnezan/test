"""Update Linear issue titles when status changes to "to research"."""

from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any

PREFIX = "Cursor researching"


def _normalize(value: Any) -> str:
    """Normalize strings for case-insensitive comparisons."""
    if value is None:
        return ""
    text = str(value).strip().lower()
    text = re.sub(r"[-_]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


def _context(payload: dict[str, Any]) -> dict[str, Any]:
    trigger_context = payload.get("triggerContext")
    if isinstance(trigger_context, dict):
        return trigger_context
    return payload


def _already_prefixed(title: str, prefix: str = PREFIX) -> bool:
    return _normalize(title).startswith(_normalize(prefix))


def _is_to_research_status_change(context: dict[str, Any]) -> bool:
    if _normalize(context.get("trigger")) != "status changed":
        return False

    new_status = context.get("newStatus")
    if new_status is None:
        new_status = context.get("status")
    return _normalize(new_status) == "to research"


def update_issue_title(payload: dict[str, Any], prefix: str = PREFIX) -> str:
    """Return updated title with prefix when moving to "to research"."""
    context = _context(payload)
    title = context.get("title")
    if not isinstance(title, str) or not title.strip():
        return ""

    if not _is_to_research_status_change(context):
        return title

    if _already_prefixed(title, prefix=prefix):
        return title

    return f"{prefix} - {title}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description='Prefix Linear issue title when status changes to "to research".'
    )
    parser.add_argument(
        "--input",
        help="Path to JSON payload file. If omitted, payload is read from stdin.",
    )
    args = parser.parse_args()

    if args.input:
        with open(args.input, "r", encoding="utf-8") as infile:
            payload = json.load(infile)
    else:
        payload = json.load(sys.stdin)

    print(json.dumps({"updatedTitle": update_issue_title(payload)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
