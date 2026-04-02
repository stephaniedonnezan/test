#!/usr/bin/env python3
"""Helpers for updating Linear issue titles based on status changes."""

from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any

RESEARCHING_MARKER = "Cursor researching"


def _normalize_token(value: str) -> str:
    """Normalize labels for case-insensitive comparisons."""
    return re.sub(r"\s+", " ", value.replace("_", " ").replace("-", " ")).strip().lower()


def _extract_trigger_context(payload: dict[str, Any]) -> dict[str, Any]:
    """Support either raw trigger payloads or wrapper payloads."""
    trigger_context = payload.get("triggerContext")
    if isinstance(trigger_context, dict):
        return trigger_context
    return payload


def _add_marker_to_title(title: str, marker: str = RESEARCHING_MARKER) -> str:
    """Prefix title with marker while avoiding duplicate prefixes."""
    clean_title = title.strip()
    if _normalize_token(clean_title).startswith(_normalize_token(marker)):
        return clean_title
    if clean_title in {"", "[]"}:
        return marker
    return f"{marker} - {clean_title}"


def maybe_update_issue_title(payload: dict[str, Any], marker: str = RESEARCHING_MARKER) -> str | None:
    """Return updated title when issue status changes to 'to research'."""
    context = _extract_trigger_context(payload)

    trigger = _normalize_token(str(context.get("trigger", "")))
    if trigger and trigger != "status changed":
        return None

    new_status = _normalize_token(str(context.get("newStatus", context.get("status", ""))))
    if new_status != "to research":
        return None

    current_title = str(context.get("title", ""))
    return _add_marker_to_title(current_title, marker=marker)


def _load_payload(path: str | None) -> dict[str, Any]:
    if path:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)
    raw = sys.stdin.read().strip()
    if not raw:
        raise ValueError("No JSON payload provided via stdin.")
    return json.loads(raw)


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply Linear issue title updates for research status.")
    parser.add_argument(
        "--input",
        help="Path to JSON payload file. If omitted, reads payload from stdin.",
    )
    args = parser.parse_args()

    payload = _load_payload(args.input)
    updated_title = maybe_update_issue_title(payload)
    print(json.dumps({"updatedTitle": updated_title}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
