#!/usr/bin/env python3
"""Helpers for updating Linear issue titles based on status changes."""

from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any, Mapping

RESEARCHING_PREFIX = "Cursor researching"
RESEARCHING_MARKER = RESEARCHING_PREFIX
TO_RESEARCH_STATUS = "to research"

_RESEARCHING_PREFIX_PATTERN = re.compile(
    r"^\s*cursor researching(?:\s*[-:|]\s*|\s+)?",
    re.IGNORECASE,
)


def _normalize_token(value: str | None) -> str:
    """Normalize labels for case-insensitive comparisons."""
    if not value:
        return ""
    expanded = value.replace("_", " ").replace("-", " ")
    return " ".join(expanded.split()).strip().lower()


def _extract_trigger_context(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    """Support either raw trigger context payloads or nested wrappers."""
    trigger_context = payload.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        return trigger_context
    return payload


def with_researching_prefix(title: str) -> str:
    """Return title with a single researching prefix."""
    stripped_title = title.strip()
    if not stripped_title or stripped_title == "[]":
        return RESEARCHING_PREFIX

    if _RESEARCHING_PREFIX_PATTERN.match(stripped_title):
        return stripped_title

    return f"{RESEARCHING_PREFIX} - {stripped_title}"


def _is_to_research_status(context: Mapping[str, Any]) -> bool:
    status = _normalize_token(str(context.get("newStatus") or context.get("status") or ""))
    return status == TO_RESEARCH_STATUS


def _is_status_change_trigger(context: Mapping[str, Any]) -> bool:
    trigger = _normalize_token(str(context.get("trigger", "")))
    return not trigger or trigger == "status changed"


def maybe_update_issue_title(payload: Mapping[str, Any]) -> str | None:
    """Return title with researching prefix when status changes to to research."""
    context = _extract_trigger_context(payload)

    if not _is_status_change_trigger(context):
        return None
    if not _is_to_research_status(context):
        return None

    current_title = str(context.get("title", ""))
    return with_researching_prefix(current_title)


def updated_title_for_status_change(payload: Mapping[str, Any]) -> str | None:
    """Return updated title only when a change is needed."""
    context = _extract_trigger_context(payload)

    if not _is_status_change_trigger(context):
        return None
    if not _is_to_research_status(context):
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
    parser = argparse.ArgumentParser(description="Apply Linear issue title updates for research status.")
    parser.add_argument(
        "--input",
        help="Path to JSON payload file. If omitted, reads payload from stdin.",
    )
    args = parser.parse_args()

    payload = _load_payload(args.input)
    updated_title = updated_title_for_status_change(payload)
    print(json.dumps({"updatedTitle": updated_title}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
