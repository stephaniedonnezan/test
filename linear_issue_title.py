"""Rules for mutating Linear issue titles from status-change events."""

from __future__ import annotations

import json
import sys
from typing import Any

CURSOR_RESEARCHING_PREFIX = "Cursor researching"


def _normalize(value: Any) -> str:
    """Safely normalize unknown values to lowercase comparable text."""
    if value is None:
        return ""
    return str(value).strip().lower()


def update_title_for_status_change(
    title: str,
    new_status: str,
    prefix: str = CURSOR_RESEARCHING_PREFIX,
) -> str:
    """Return an updated title for a Linear status change."""
    if _normalize(new_status) != "to research":
        return title

    normalized_title = _normalize(title)
    normalized_prefix = _normalize(prefix)

    if normalized_title.startswith(normalized_prefix):
        return title

    return f"{prefix}: {title}"


def build_title_update_from_event(event: dict[str, Any]) -> dict[str, Any]:
    """Generate a title update payload from a Linear automation event."""
    context = event.get("triggerContext", event)
    title = str(context.get("title", ""))
    updated_title = update_title_for_status_change(
        title=title,
        new_status=str(context.get("newStatus", "")),
    )

    return {
        "should_update": updated_title != title,
        "title": updated_title,
    }


def main() -> int:
    """Read event JSON from stdin and print update payload as JSON."""
    try:
        raw_input = sys.stdin.read()
        event = json.loads(raw_input)
        result = build_title_update_from_event(event)
    except json.JSONDecodeError as exc:
        print(json.dumps({"error": f"invalid JSON input: {exc}"}))
        return 1

    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
