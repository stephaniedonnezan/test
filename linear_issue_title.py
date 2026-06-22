#!/usr/bin/env python3
"""Apply Linear issue title updates for Cursor research automations."""

from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any


RESEARCH_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_CHANGED_TRIGGER = "status changed"


def _normalize(value: Any) -> str:
    """Normalize labels from Linear payloads for tolerant comparisons."""
    if value is None:
        return ""
    text = str(value).replace("_", " ").replace("-", " ")
    return re.sub(r"\s+", " ", text).strip().lower()


def _trigger_context(event: dict[str, Any]) -> dict[str, Any]:
    """Return Linear trigger data from wrapped or root-level payloads."""
    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, dict):
        return trigger_context
    return event


def should_prefix_title(event: dict[str, Any]) -> bool:
    """Return True when a Linear issue moved to the 'to research' status."""
    context = _trigger_context(event)
    trigger = _normalize(context.get("trigger"))
    new_status = _normalize(context.get("newStatus", context.get("status")))

    return trigger == STATUS_CHANGED_TRIGGER and new_status == TARGET_STATUS


def with_research_prefix(title: str) -> str:
    """Return the title with exactly one Cursor research prefix."""
    cleaned = title.strip()
    if not cleaned:
        return RESEARCH_PREFIX
    if _normalize(cleaned).startswith(_normalize(RESEARCH_PREFIX)):
        return cleaned
    return f"{RESEARCH_PREFIX} {cleaned}"


def apply_title_rule(event: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of the event with the research title rule applied."""
    updated = dict(event)
    context = dict(_trigger_context(event))

    if should_prefix_title(event):
        context["title"] = with_research_prefix(str(context.get("title", "")))
        if isinstance(event.get("triggerContext"), dict):
            updated["triggerContext"] = context
        else:
            updated.update(context)

    return updated


def maybe_update_issue_title(event: dict[str, Any]) -> str | None:
    """Return the updated title, or None when the event should not change."""
    if not should_prefix_title(event):
        return None
    return with_research_prefix(str(_trigger_context(event).get("title", "")))


def _load_payload(path: str | None) -> dict[str, Any]:
    if path:
        with open(path, "r", encoding="utf-8") as file_obj:
            return json.load(file_obj)
    return json.load(sys.stdin)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Add 'Cursor researching' to a Linear issue title when the issue "
            "status changes to 'to research'."
        )
    )
    parser.add_argument(
        "--payload-file",
        help="Path to a JSON payload file. If omitted, JSON is read from stdin.",
    )
    args = parser.parse_args()

    updated = apply_title_rule(_load_payload(args.payload_file))
    print(json.dumps(updated, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
