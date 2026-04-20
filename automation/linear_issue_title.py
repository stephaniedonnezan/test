"""Helpers for updating Linear issue titles from status change events."""

from __future__ import annotations

import json
import sys
from typing import Any

RESEARCH_STATUS = "to research"
RESEARCH_PREFIX = "Cursor researching"


def _normalize(value: str | None) -> str:
    """Return a lowercase, whitespace-normalized string."""
    if value is None:
        return ""
    return " ".join(value.strip().lower().split())


def _extract_context(payload: dict[str, Any]) -> dict[str, Any]:
    """Support both nested triggerContext and top-level event shapes."""
    trigger_context = payload.get("triggerContext")
    if isinstance(trigger_context, dict):
        return trigger_context
    return payload


def build_research_title(title: str) -> str:
    """Prefix title with 'Cursor researching' unless already present."""
    stripped = title.strip()
    if _normalize(stripped).startswith(_normalize(RESEARCH_PREFIX)):
        return stripped
    return f"{RESEARCH_PREFIX}: {stripped}"


def maybe_prefix_title_on_status_change(payload: dict[str, Any]) -> str | None:
    """Return updated title when status changes to 'to research'."""
    context = _extract_context(payload)

    if _normalize(context.get("newStatus")) != RESEARCH_STATUS:
        return None

    title = context.get("title")
    if not isinstance(title, str) or not title.strip():
        return None

    return build_research_title(title)


def build_linear_title_update(payload: dict[str, Any]) -> dict[str, str] | None:
    """Create a minimal title update payload for Linear mutation calls."""
    context = _extract_context(payload)
    issue_id = context.get("id")
    updated_title = maybe_prefix_title_on_status_change(payload)

    if not isinstance(issue_id, str) or not issue_id.strip() or updated_title is None:
        return None

    return {"id": issue_id.strip(), "title": updated_title}


def main() -> int:
    """Read event JSON from stdin and print title update payload when needed."""
    payload = json.load(sys.stdin)
    update = build_linear_title_update(payload)
    if update is None:
        return 0
    json.dump(update, sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
