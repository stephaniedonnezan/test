"""Helpers for updating Linear issue titles on status changes.

Rule:
- When an issue status changes to "to research", prefix its title with
  "Cursor researching".
"""

from __future__ import annotations

import copy
import json
import re
import sys
from typing import Any

RESEARCH_PREFIX = "Cursor researching"


def _normalize_status(status: str) -> str:
    normalized = status.replace("_", " ").replace("-", " ").strip().lower()
    return re.sub(r"\s+", " ", normalized)


def should_add_research_prefix(trigger_context: dict[str, Any]) -> bool:
    """Return True when a payload represents a move to 'to research'."""
    trigger = str(trigger_context.get("trigger", "")).strip().lower()
    new_status = _normalize_status(str(trigger_context.get("newStatus", "")))
    return trigger == "status_changed" and new_status == "to research"


def prefix_title(title: str, prefix: str = RESEARCH_PREFIX) -> str:
    """Add the researching prefix once, preserving idempotency."""
    clean_title = title.strip()
    if not clean_title:
        return prefix

    if clean_title.lower().startswith(prefix.lower()):
        return clean_title

    return f"{prefix}: {clean_title}"


def apply_research_title_prefix(event_payload: dict[str, Any]) -> dict[str, Any]:
    """Return a copied payload with title updated when status is 'to research'."""
    updated_payload = copy.deepcopy(event_payload)
    trigger_context = updated_payload.get("triggerContext")

    if not isinstance(trigger_context, dict):
        return updated_payload

    if not should_add_research_prefix(trigger_context):
        return updated_payload

    updated_title = prefix_title(str(trigger_context.get("title", "")))
    trigger_context["title"] = updated_title

    # Convenience field for downstream consumers.
    updated_payload["updatedTitle"] = updated_title
    return updated_payload


def main() -> int:
    """CLI: read JSON from stdin and emit updated JSON to stdout."""
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON input: {exc}", file=sys.stderr)
        return 1

    if not isinstance(payload, dict):
        print("Input payload must be a JSON object.", file=sys.stderr)
        return 1

    updated = apply_research_title_prefix(payload)
    json.dump(updated, sys.stdout, ensure_ascii=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
