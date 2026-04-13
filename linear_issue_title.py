"""Update Linear issue titles for status-change automation events."""

from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any

TARGET_STATUS = "to research"
TARGET_TRIGGER = "status changed"
TITLE_PREFIX = "Cursor researching"


def _normalize_token(value: Any) -> str:
    """Normalize text to compare trigger/status values safely."""
    if not isinstance(value, str):
        return ""
    normalized = re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()
    return re.sub(r"\s+", " ", normalized)


def _already_prefixed(title: str) -> bool:
    """Detect whether title already starts with the expected prefix."""
    return bool(re.match(r"^\s*cursor[\s\-_]+researching\b", title, flags=re.IGNORECASE))


def update_issue_title(payload: dict[str, Any]) -> str:
    """Return the updated title based on Linear status-change payload."""
    context = payload.get("triggerContext")
    data: dict[str, Any] = context if isinstance(context, dict) else payload

    title = data.get("title")
    if not isinstance(title, str) or not title.strip():
        return ""

    if _normalize_token(data.get("trigger")) != TARGET_TRIGGER:
        return title

    new_status = data.get("newStatus", data.get("status"))
    if _normalize_token(new_status) != TARGET_STATUS:
        return title

    if _already_prefixed(title):
        return title

    return f"{TITLE_PREFIX} - {title}"


def _read_payload(input_path: str | None) -> dict[str, Any]:
    if input_path:
        with open(input_path, "r", encoding="utf-8") as file:
            return json.load(file)
    return json.load(sys.stdin)


def main() -> int:
    parser = argparse.ArgumentParser(description="Update Linear issue title for research status changes.")
    parser.add_argument(
        "--input",
        help="Path to JSON payload file. If omitted, reads from stdin.",
    )
    args = parser.parse_args()

    payload = _read_payload(args.input)
    updated_title = update_issue_title(payload)
    print(json.dumps({"updatedTitle": updated_title}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
