#!/usr/bin/env python3
"""Linear issue title prefix automation for "to research" status changes."""

from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any, Dict

TARGET_TRIGGER = "status_changed"
TARGET_STATUS = "to research"
PREFIX = "Cursor researching - "
_PREFIX_PATTERN = re.compile(r"^\s*cursor\s+researching(?:\s*[-:]\s*|\s+)", re.IGNORECASE)


def _normalize_text(value: Any) -> str:
    """Normalize text for case/whitespace-insensitive comparisons."""
    if value is None:
        return ""
    text = str(value)
    text = re.sub(r"[\s_-]+", " ", text.strip().lower())
    return text


def _extract_title(payload: Dict[str, Any]) -> str:
    """Extract issue title from common payload shapes."""
    if isinstance(payload.get("title"), str):
        return payload["title"]

    issue = payload.get("issue")
    if isinstance(issue, dict) and isinstance(issue.get("title"), str):
        return issue["title"]

    trigger_context = payload.get("triggerContext")
    if isinstance(trigger_context, dict) and isinstance(trigger_context.get("title"), str):
        return trigger_context["title"]

    return ""


def _extract_trigger(payload: Dict[str, Any]) -> str:
    """Extract trigger value from common payload shapes."""
    if "trigger" in payload:
        return _normalize_text(payload.get("trigger"))

    trigger_context = payload.get("triggerContext")
    if isinstance(trigger_context, dict):
        return _normalize_text(trigger_context.get("trigger"))

    return ""


def _extract_status(payload: Dict[str, Any]) -> str:
    """Extract status value from common payload shapes."""
    if "newStatus" in payload:
        return _normalize_text(payload.get("newStatus"))
    if "status" in payload:
        return _normalize_text(payload.get("status"))

    trigger_context = payload.get("triggerContext")
    if isinstance(trigger_context, dict):
        if "newStatus" in trigger_context:
            return _normalize_text(trigger_context.get("newStatus"))
        if "status" in trigger_context:
            return _normalize_text(trigger_context.get("status"))

    return ""


def compute_updated_title(payload: Dict[str, Any]) -> str:
    """
    Return updated title if payload represents a "to research" status change.

    If criteria are not met, return the original title.
    """
    title = _extract_title(payload)
    trigger = _extract_trigger(payload)
    status = _extract_status(payload)

    if trigger != _normalize_text(TARGET_TRIGGER) or status != _normalize_text(TARGET_STATUS):
        return title

    if not title:
        return "Cursor researching"

    if _PREFIX_PATTERN.match(title):
        return title

    return f"{PREFIX}{title}"


def _load_payload(path: str | None) -> Dict[str, Any]:
    """Load JSON payload from path or stdin."""
    raw = ""
    if path:
        with open(path, "r", encoding="utf-8") as handle:
            raw = handle.read()
    else:
        raw = sys.stdin.read()

    if not raw.strip():
        return {}
    return json.loads(raw)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        help="Path to JSON payload (reads stdin if omitted).",
    )
    args = parser.parse_args(argv)

    payload = _load_payload(args.input)
    updated_title = compute_updated_title(payload)
    print(json.dumps({"updatedTitle": updated_title}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
