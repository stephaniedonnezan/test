"""Helpers for updating Linear issue titles on status changes.

The core behavior implemented here:
- only react to status-change triggers
- when the new status is "to research", prefix the title with
  "Cursor researching" (without duplicating the prefix)
"""

from __future__ import annotations

import json
import re
import sys
from typing import Any

DEFAULT_PREFIX = "Cursor researching"
STATUS_TO_RESEARCH = "to research"
STATUS_CHANGED = "status changed"


def _normalize_token(value: Any) -> str:
    """Normalize text for case-insensitive comparisons."""
    if value is None:
        return ""
    text = str(value).strip().lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def _starts_with_prefix(title: str, prefix: str) -> bool:
    """Return True when title already starts with the given prefix."""
    normalized_title = _normalize_token(title)
    normalized_prefix = _normalize_token(prefix)
    return normalized_title.startswith(normalized_prefix)


def _build_prefixed_title(title: str, prefix: str) -> str:
    """Build a prefixed title, preserving the original title text."""
    cleaned = (title or "").strip()
    if not cleaned:
        return prefix

    if _starts_with_prefix(cleaned, prefix):
        return cleaned

    return f"{prefix}: {cleaned}"


def _status_changed_to_research(trigger_context: dict[str, Any]) -> bool:
    """Check whether the event is a status change to 'to research'."""
    trigger = _normalize_token(trigger_context.get("trigger"))
    if trigger != STATUS_CHANGED:
        return False

    new_status = trigger_context.get("newStatus")
    if new_status is None:
        new_status = trigger_context.get("status")

    return _normalize_token(new_status) == STATUS_TO_RESEARCH


def build_issue_title_update(
    event: dict[str, Any], prefix: str = DEFAULT_PREFIX
) -> dict[str, Any] | None:
    """Return an issue title update payload when event matches, else None.

    Expected event shape (minimal):
    {
      "triggerContext": {
        "trigger": "status_changed",
        "newStatus": "to research",
        "title": "<issue title>",
        "id": "<issue id>"
      }
    }
    """
    trigger_context = event.get("triggerContext")
    if not isinstance(trigger_context, dict):
        return None

    if not _status_changed_to_research(trigger_context):
        return None

    title = trigger_context.get("title")
    if title is None:
        return None

    issue_id = trigger_context.get("id")
    if issue_id is None:
        return None

    updated_title = _build_prefixed_title(str(title), prefix=prefix)
    if str(title).strip() == updated_title:
        return None

    return {
        "action": "update_issue_title",
        "issueId": str(issue_id),
        "title": updated_title,
    }


def _main() -> int:
    """CLI entrypoint: read JSON event from stdin, write JSON update or null."""
    raw_input = sys.stdin.read().strip()
    if not raw_input:
        print("null")
        return 0

    event = json.loads(raw_input)
    result = build_issue_title_update(event)
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
