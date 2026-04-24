#!/usr/bin/env python3
"""Utilities for updating Linear issue titles from status-change webhooks."""

from __future__ import annotations

import json
import sys
from typing import Any

RESEARCHING_MARKER = "Cursor researching"


def normalize_status(value: Any) -> str:
    """Normalize a status string for comparison."""
    if not isinstance(value, str):
        return ""
    return " ".join(value.strip().lower().split())


def should_prefix_researching(trigger_context: dict[str, Any]) -> bool:
    """Return True when an issue moved to the 'to research' status."""
    if not isinstance(trigger_context, dict):
        return False

    status = normalize_status(trigger_context.get("newStatus"))
    trigger = normalize_status(trigger_context.get("trigger"))
    webhook_type = normalize_status(trigger_context.get("webhookType"))
    trigger_type = normalize_status(trigger_context.get("triggerType"))

    return (
        status == "to research"
        and trigger == "status_changed"
        and webhook_type == "issue"
        and trigger_type == "linear"
    )


def add_researching_prefix(title: str) -> str:
    """Prefix a title with the researching marker once."""
    clean_title = title.strip()
    if not clean_title:
        return RESEARCHING_MARKER

    if normalize_status(clean_title).startswith(normalize_status(RESEARCHING_MARKER)):
        return clean_title

    return f"{RESEARCHING_MARKER}: {clean_title}"


def updated_title_from_payload(payload: dict[str, Any]) -> str | None:
    """Return the updated title, or None when no title change is needed."""
    trigger_context = payload.get("triggerContext", payload)
    if not should_prefix_researching(trigger_context):
        return None

    title = trigger_context.get("title")
    if not isinstance(title, str):
        return RESEARCHING_MARKER

    return add_researching_prefix(title)


def main() -> int:
    """Read an event payload from stdin and print a JSON response."""
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        print(json.dumps({"error": "Invalid JSON payload"}))
        return 1

    if not isinstance(payload, dict):
        print(json.dumps({"error": "Payload must be a JSON object"}))
        return 1

    updated_title = updated_title_from_payload(payload)
    if updated_title is None:
        print(json.dumps({"title": None, "updated": False}))
        return 0

    print(json.dumps({"title": updated_title, "updated": True}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
