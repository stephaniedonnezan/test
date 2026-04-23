#!/usr/bin/env python3
"""Helpers for updating Linear issue titles based on status changes."""

from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any, Mapping

RESEARCH_PREFIX = "Cursor researching"
TO_RESEARCH_STATUS = "to research"


def _normalize(value: Any) -> str:
    """Normalize labels for case-insensitive comparisons."""
    if value is None:
        return ""
    text = str(value).replace("_", " ").replace("-", " ")
    return " ".join(text.split()).strip().lower()


def _extract_context(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    """Support both wrapped and raw trigger payloads."""
    context = payload.get("triggerContext")
    if isinstance(context, Mapping):
        return context
    return payload


def _prefixed_pattern(prefix: str) -> re.Pattern[str]:
    return re.compile(
        rf"^\s*{re.escape(prefix)}(?:\s*[-:|]\s*|\s+)?",
        re.IGNORECASE,
    )


def should_prefix_research_title(trigger_context: Mapping[str, Any]) -> bool:
    """Return True when this is an issue status-change to 'to research'."""
    if _normalize(trigger_context.get("trigger")) != "status changed":
        return False

    webhook_type = _normalize(trigger_context.get("webhookType"))
    if webhook_type and webhook_type != "issue":
        return False

    return (
        _normalize(trigger_context.get("newStatus") or trigger_context.get("status"))
        == TO_RESEARCH_STATUS
    )


def prefix_research_title(title: str, prefix: str = RESEARCH_PREFIX) -> str:
    """Prefix an issue title with the research marker once."""
    clean_title = title.strip()
    if not clean_title:
        return prefix
    if _prefixed_pattern(prefix).match(clean_title):
        return clean_title
    return f"{prefix} {clean_title}"


def _add_marker_to_title(title: str, marker: str = RESEARCH_PREFIX) -> str:
    """Prefix a title with marker while avoiding duplicates."""
    clean_title = title.strip()
    if _prefixed_pattern(marker).match(clean_title):
        return clean_title
    if clean_title in {"", "[]"}:
        return marker
    return f"{marker} - {clean_title}"


def maybe_update_issue_title(payload: Mapping[str, Any], marker: str = RESEARCH_PREFIX) -> str | None:
    """Return updated title when issue status moves to 'to research'."""
    context = _extract_context(payload)

    trigger = _normalize(context.get("trigger"))
    if trigger and trigger != "status changed":
        return None

    webhook_type = _normalize(context.get("webhookType"))
    if webhook_type and webhook_type != "issue":
        return None

    new_status = _normalize(context.get("newStatus") or context.get("status"))
    if new_status != TO_RESEARCH_STATUS:
        return None

    current_title = str(context.get("title", ""))
    return _add_marker_to_title(current_title, marker=marker)


def update_issue_title_from_event(event: Mapping[str, Any]) -> str | None:
    """Return an updated title when event matches the 'to research' transition."""
    trigger_context = _extract_context(event)
    if not should_prefix_research_title(trigger_context):
        return None

    title = trigger_context.get("title")
    if not isinstance(title, str):
        return None

    return prefix_research_title(title)


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
    updated_title = maybe_update_issue_title(payload)
    print(json.dumps({"updatedTitle": updated_title}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
