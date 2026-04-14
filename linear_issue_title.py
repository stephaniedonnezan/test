"""Linear status-change title mutation helpers.

This module adds a "Cursor researching" prefix when an issue moves to
"to research" status.
"""

from __future__ import annotations

import json
import sys
from typing import Any

PREFIX = "Cursor researching"


def _is_to_research(status: str) -> bool:
    return status.strip().lower() == "to research"


def _prefixed_title(title: str) -> str:
    if title.strip().lower().startswith(PREFIX.lower()):
        return title
    return f"{PREFIX} - {title}"


def compute_updated_title(payload: dict[str, Any]) -> str | None:
    """Return an updated title when the event should mutate it.

    Expected payload shape:
      {
        "triggerContext": {
          "trigger": "status_changed",
          "newStatus": "To research",
          "title": "Issue title"
        }
      }
    """

    trigger_context = payload.get("triggerContext", {})
    if trigger_context.get("trigger") != "status_changed":
        return None

    if not _is_to_research(str(trigger_context.get("newStatus", ""))):
        return None

    title = str(trigger_context.get("title", "")).strip()
    if not title:
        return None

    return _prefixed_title(title)


def main() -> int:
    """Read payload JSON from stdin and print mutation output."""

    payload = json.load(sys.stdin)
    updated_title = compute_updated_title(payload)
    print(json.dumps({"updatedTitle": updated_title}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
