#!/usr/bin/env python3
"""Helpers for updating Linear issue titles when status changes."""

from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any, Mapping

RESEARCHING_PREFIX = "Cursor researching"
TO_RESEARCH_STATUS = "to research"

_RESEARCHING_PREFIX_PATTERN = re.compile(
    r"^\s*cursor researching(?:\s*[-:|]\s*|\s+)?",
    re.IGNORECASE,
)


def _normalize_token(value: str | None) -> str:
    """Normalize labels/tokens for case-insensitive comparisons."""
    if not value:
        return ""
    normalized = value.replace("_", " ").replace("-", " ")
    return " ".join(normalized.split()).strip().lower()


def _extract_context(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    """Support wrappers that place the issue payload under triggerContext."""
    context = payload.get("triggerContext")
    if isinstance(context, Mapping):
        return context
    return payload


def with_researching_prefix(title: str) -> str:
    """Return title with a single researching prefix."""
    stripped_title = title.strip()
    if not stripped_title:
        return RESEARCHING_PREFIX

    if _RESEARCHING_PREFIX_PATTERN.match(stripped_title):
        return stripped_title

    return f"{RESEARCHING_PREFIX} - {stripped_title}"


def updated_title_for_status_change(payload: Mapping[str, Any]) -> str | None:
    """Return updated issue title when status moves to 'to research'."""
    context = _extract_context(payload)

    trigger = _normalize_token(str(context.get("trigger", "")))
    if trigger and trigger != "status changed":
        return None

    status = _normalize_token(str(context.get("newStatus") or context.get("status") or ""))
    if status != TO_RESEARCH_STATUS:
        return None

    current_title = str(context.get("title", "")).strip()
    next_title = with_researching_prefix(current_title)
    if next_title == current_title:
        return None
    return next_title


def _load_payload(path: str | None) -> dict[str, Any]:
    if path:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)
    raw = sys.stdin.read().strip()
    if not raw:
        raise ValueError("No JSON payload provided via stdin.")
    return json.loads(raw)


def main() -> int:
    parser = argparse.ArgumentParser(description="Update Linear issue title for research status changes.")
    parser.add_argument("--input", help="Path to JSON payload file. If omitted, reads JSON from stdin.")
    args = parser.parse_args()

    payload = _load_payload(args.input)
    print(json.dumps({"updatedTitle": updated_title_for_status_change(payload)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
