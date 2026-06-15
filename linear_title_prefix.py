"""Helpers for adding a research marker to Linear issue titles."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Mapping
from typing import Any

RESEARCH_TITLE_MARKER = "Cursor researching"
RESEARCH_STATUS_NAME = "to research"
STATUS_CHANGED_TRIGGER = "status changed"

EXISTING_RESEARCH_MARKER_PATTERN = re.compile(
    rf"^\s*(?:\[\s*)?{re.escape(RESEARCH_TITLE_MARKER)}(?:\s*\])?(?:\s*[-:]\s*|\s+)?",
    flags=re.IGNORECASE,
)
EMPTY_TITLE_MARKER_PATTERN = re.compile(r"^(\s*)\[\s*\]")


def _normalize_whitespace(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _normalize_token(value: str) -> str:
    return _normalize_whitespace(re.sub(r"[^a-z0-9]+", " ", value.lower()))


def _is_status_changed_trigger(trigger: str) -> bool:
    return _normalize_token(trigger) == STATUS_CHANGED_TRIGGER


def _add_research_marker(title: str, marker: str = RESEARCH_TITLE_MARKER) -> str:
    """Add the research marker while preserving existing title conventions."""
    if EXISTING_RESEARCH_MARKER_PATTERN.match(title):
        return title

    marker_match = EMPTY_TITLE_MARKER_PATTERN.match(title)
    if marker_match:
        leading_whitespace = marker_match.group(1)
        rest_of_title = title[marker_match.end() :]
        return f"{leading_whitespace}[{marker}]{rest_of_title}"

    clean_title = title.strip()
    if not clean_title:
        return marker
    return f"{marker} - {clean_title}"


def update_issue_title_for_status(title: str, new_status: str) -> str:
    """Return title with the research marker when status is `to research`."""
    if _normalize_whitespace(new_status) == RESEARCH_STATUS_NAME:
        return _add_research_marker(title)
    return title


def _extract_trigger_context(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    trigger_context = payload.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        return trigger_context
    return payload


def derive_updated_title(payload: Mapping[str, Any]) -> str | None:
    """Derive the updated Linear issue title from an automation payload.

    The Cursor automation payload nests Linear fields under ``triggerContext``.
    Tests also cover the raw context shape so this helper can be reused in small
    scripts without wrapping the payload first.
    """
    trigger_context = _extract_trigger_context(payload)

    trigger = trigger_context.get("trigger")
    if isinstance(trigger, str) and not _is_status_changed_trigger(trigger):
        return None

    title = trigger_context.get("title")
    new_status = trigger_context.get("newStatus", trigger_context.get("status"))
    if not isinstance(title, str) or not isinstance(new_status, str):
        return None

    updated_title = update_issue_title_for_status(title=title, new_status=new_status)
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
        description="Add Cursor researching to Linear issue titles moved to to research."
    )
    parser.add_argument(
        "--input",
        help="Path to input JSON payload (reads from stdin if omitted).",
    )
    args = parser.parse_args(argv)

    payload = _load_payload(args.input)
    updated_title = derive_updated_title(payload)
    print(json.dumps({"updatedTitle": updated_title}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
