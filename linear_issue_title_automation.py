"""Helpers for updating Linear issue titles from webhook events."""

from __future__ import annotations

import json
import sys
from typing import Any

RESEARCH_STATUS = "to research"
RESEARCH_PREFIX = "Cursor researching"
TITLE_SEPARATOR = " - "


def _normalize(value: str | None) -> str:
    """Normalize a status/title fragment for case-insensitive checks."""
    if value is None:
        return ""
    return value.strip().lower()


def _is_status_change_to_research(payload: dict[str, Any]) -> bool:
    """Return True only for `status_changed` events moving to `to research`."""
    trigger_context = payload.get("triggerContext") or {}
    trigger = _normalize(trigger_context.get("trigger"))
    new_status = _normalize(trigger_context.get("newStatus"))
    return trigger == "status_changed" and new_status == RESEARCH_STATUS


def _is_already_prefixed(title: str) -> bool:
    """Detect if title already starts with the expected research prefix."""
    normalized_title = _normalize(title)
    normalized_prefix = _normalize(RESEARCH_PREFIX)
    return normalized_title.startswith(normalized_prefix)


def build_issue_title_update(payload: dict[str, Any]) -> dict[str, str] | None:
    """
    Build a title update payload for Linear when status changes to `to research`.

    Returns:
        - {"title": "<new title>"} when title should be updated.
        - None when the event does not match the status rule or no change is needed.
    """
    if not _is_status_change_to_research(payload):
        return None

    trigger_context = payload.get("triggerContext") or {}
    title = (trigger_context.get("title") or "").strip()
    if not title or _is_already_prefixed(title):
        return None

    return {"title": f"{RESEARCH_PREFIX}{TITLE_SEPARATOR}{title}"}


def _main() -> int:
    """
    Read a webhook payload from stdin and print a JSON patch or `null`.

    Example:
      echo '{"triggerContext": {"trigger":"status_changed","newStatus":"to research","title":"Issue"}}' \
          | python linear_issue_title_automation.py
    """
    payload = json.load(sys.stdin)
    result = build_issue_title_update(payload)
    json.dump(result, sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
