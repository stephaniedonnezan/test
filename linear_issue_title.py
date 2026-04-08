#!/usr/bin/env python3
"""Update Linear issue titles for specific status changes."""

from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any, Dict

PREFIX = "Cursor researching - "


def _normalize(value: Any) -> str:
    """Lowercase and normalize separators for flexible comparisons."""
    if value is None:
        return ""
    normalized = re.sub(r"[\s_-]+", " ", str(value).strip().lower())
    return normalized


def _has_prefix(title: str) -> bool:
    return _normalize(title).startswith(_normalize(PREFIX))


def _extract_context(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Support both automation wrapper payloads and direct trigger payloads."""
    trigger_context = payload.get("triggerContext")
    if isinstance(trigger_context, dict):
        return trigger_context
    return payload


def update_title(payload: Dict[str, Any]) -> Dict[str, str]:
    """Return a JSON-serializable dict containing the updated title."""
    context = _extract_context(payload)

    trigger = _normalize(context.get("trigger"))
    new_status = _normalize(context.get("newStatus") or context.get("status"))
    title = str(context.get("title") or "")

    updated_title = title
    if (
        trigger == "status changed"
        and new_status == "to research"
        and title
        and not _has_prefix(title)
    ):
        updated_title = f"{PREFIX}{title}"

    return {"updatedTitle": updated_title}


def _read_payload(input_path: str | None) -> Dict[str, Any]:
    if input_path:
        with open(input_path, "r", encoding="utf-8") as file:
            return json.load(file)

    raw = sys.stdin.read().strip()
    if not raw:
        return {}
    return json.loads(raw)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Update issue title when status changes to to research."
    )
    parser.add_argument(
        "--input",
        dest="input_path",
        help="Path to JSON payload file. Defaults to stdin when omitted.",
    )
    args = parser.parse_args()

    payload = _read_payload(args.input_path)
    result = update_title(payload)
    print(json.dumps(result, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
