#!/usr/bin/env python3
"""Linear status-change title prefix automation.

Reads automation payload JSON (from stdin or --input file) and outputs:
{"updatedTitle": "<title>"}

When trigger indicates a status change and the new status is "to research",
the title is prefixed with "Cursor researching - " unless it is already present.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any, Dict, Optional

PREFIX = "Cursor researching - "
_PREFIX_RE = re.compile(r"^\s*cursor\s+researching(?:\s*[:\-])?\s*", re.IGNORECASE)


def _normalize_status(value: Optional[str]) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", str(value).strip().lower())


def _normalize_trigger(value: Optional[str]) -> str:
    if not value:
        return ""
    normalized = str(value).strip().lower()
    normalized = re.sub(r"[\s\-]+", "_", normalized)
    return normalized


def _extract_trigger_context(payload: Dict[str, Any]) -> Dict[str, Any]:
    context = payload.get("triggerContext")
    if isinstance(context, dict):
        return context
    return {}


def _extract_title(payload: Dict[str, Any], context: Dict[str, Any]) -> str:
    title = payload.get("title")
    if isinstance(title, str) and title.strip():
        return title
    context_title = context.get("title")
    if isinstance(context_title, str):
        return context_title
    return ""


def _status_is_to_research(payload: Dict[str, Any], context: Dict[str, Any]) -> bool:
    status_candidates = [
        context.get("newStatus"),
        context.get("status"),
        payload.get("newStatus"),
        payload.get("status"),
    ]
    return any(_normalize_status(candidate) == "to research" for candidate in status_candidates)


def _is_status_changed_trigger(payload: Dict[str, Any], context: Dict[str, Any]) -> bool:
    trigger_candidates = [
        context.get("trigger"),
        payload.get("trigger"),
        payload.get("webhookType"),
    ]
    normalized = [_normalize_trigger(candidate) for candidate in trigger_candidates]
    return "status_changed" in normalized


def _already_prefixed(title: str) -> bool:
    return bool(_PREFIX_RE.match(title))


def build_updated_title(payload: Dict[str, Any]) -> str:
    """Return updated title according to trigger/status rules."""
    context = _extract_trigger_context(payload)
    title = _extract_title(payload, context)

    if not title:
        return title

    if _is_status_changed_trigger(payload, context) and _status_is_to_research(payload, context):
        if _already_prefixed(title):
            return title
        return f"{PREFIX}{title}"

    return title


def _read_payload(path: Optional[str]) -> Dict[str, Any]:
    if path:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)

    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    return json.loads(raw)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prefix Linear issue title when status changes to 'to research'."
    )
    parser.add_argument(
        "--input",
        "-i",
        help="Path to payload JSON file. If omitted, reads JSON from stdin.",
    )
    args = parser.parse_args()

    payload = _read_payload(args.input)
    updated_title = build_updated_title(payload)
    print(json.dumps({"updatedTitle": updated_title}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
