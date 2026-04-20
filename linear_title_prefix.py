#!/usr/bin/env python3
"""Update Linear issue titles for specific status change events."""

from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any, Dict

PREFIX = "Cursor researching"


def _normalize_token(value: Any) -> str:
    """Normalize free-form tokens for robust comparisons."""
    if value is None:
        return ""
    text = str(value).strip().lower()
    text = re.sub(r"[\s_\-]+", " ", text)
    return text


def should_prefix(payload: Dict[str, Any]) -> bool:
    """Return True when payload indicates a move to 'to research'."""
    trigger = _normalize_token(payload.get("trigger"))
    new_status = _normalize_token(payload.get("newStatus") or payload.get("status"))
    return trigger == "status changed" and new_status == "to research"


def has_prefix(title: str) -> bool:
    """Return True if title is already prefixed."""
    pattern = r"^\s*cursor\s+researching(?:\s*[:\-]\s*|\s+)"
    return re.match(pattern, title, flags=re.IGNORECASE) is not None


def update_title(payload: Dict[str, Any]) -> str:
    """Return updated title from payload, idempotently."""
    title = str(payload.get("title") or "").strip()
    if not title:
        return title

    if should_prefix(payload) and not has_prefix(title):
        return f"{PREFIX} - {title}"
    return title


def _read_payload(input_path: str | None) -> Dict[str, Any]:
    if input_path:
        with open(input_path, "r", encoding="utf-8") as handle:
            return json.load(handle)

    raw = sys.stdin.read().strip()
    if not raw:
        return {}
    return json.loads(raw)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prefix Linear issue title on to research status.")
    parser.add_argument("--input", help="Path to JSON payload file.")
    args = parser.parse_args(argv)

    payload = _read_payload(args.input)
    updated_title = update_title(payload)
    print(json.dumps({"updatedTitle": updated_title}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
