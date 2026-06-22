"""Helpers for marking Linear issue titles when they enter research."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Mapping
from typing import Any

RESEARCH_TITLE_MARKER = "Cursor researching"
RESEARCH_STATUS_NAME = "to research"

_TITLE_MARKER_PATTERN = re.compile(
    rf"^\s*{re.escape(RESEARCH_TITLE_MARKER)}(?:\s*[-:]\s*|\s+)?",
    flags=re.IGNORECASE,
)
_STATUS_CHANGED_TRIGGERS = frozenset(
    {
        "status changed",
        "status change",
        "status updated",
        "state changed",
        "state change",
        "workflow state changed",
    }
)


def _normalize_phrase(value: str) -> str:
    return re.sub(r"[\s_-]+", " ", value.strip().casefold())


def _normalize_token(value: str) -> str:
    split_camel = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return _normalize_phrase(re.sub(r"[^a-zA-Z0-9]+", " ", split_camel))


def _is_status_changed_trigger(trigger: str) -> bool:
    return _normalize_token(trigger) in _STATUS_CHANGED_TRIGGERS


def _mark_title(title: str) -> str:
    """Add the Cursor researching marker to the start of a title once."""
    if _TITLE_MARKER_PATTERN.match(title):
        return title

    clean_title = title.strip()
    if not clean_title:
        return RESEARCH_TITLE_MARKER
    return f"{RESEARCH_TITLE_MARKER} - {clean_title}"


def updated_title_for_status_change(title: str, new_status: str) -> str:
    """Return the title Linear should use after a status change."""
    if _normalize_phrase(new_status) != RESEARCH_STATUS_NAME:
        return title
    return _mark_title(title)


def _trigger_context(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    trigger_context = payload.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        return trigger_context
    return payload


def derive_updated_title(payload: Mapping[str, Any]) -> str | None:
    """Return a marked issue title for matching automation payloads.

    The Cursor automation payload provides data under ``triggerContext``. Tests
    and local scripts can also call this with that object directly.
    """
    context = _trigger_context(payload)

    trigger = context.get("trigger")
    if isinstance(trigger, str) and not _is_status_changed_trigger(trigger):
        return None

    title = context.get("title")
    new_status = context.get("newStatus", context.get("status"))
    if not isinstance(title, str) or not isinstance(new_status, str):
        return None

    updated_title = updated_title_for_status_change(title, new_status)
    if updated_title == title:
        return None
    return updated_title


def _load_payload(input_path: str | None) -> Mapping[str, Any]:
    if input_path:
        with open(input_path, encoding="utf-8") as input_file:
            payload = json.load(input_file)
    else:
        payload = json.load(sys.stdin)

    if not isinstance(payload, Mapping):
        raise ValueError("Input payload must be a JSON object.")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Add Cursor researching to Linear issue titles for research status changes."
    )
    parser.add_argument(
        "--input",
        help="Path to input JSON payload. Reads from stdin when omitted.",
    )
    args = parser.parse_args(argv)

    updated_title = derive_updated_title(_load_payload(args.input))
    print(json.dumps({"updatedTitle": updated_title}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
