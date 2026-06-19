"""Helpers for marking Linear issue titles during research status changes."""

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
TITLE_MARKER_PATTERN = re.compile(
    rf"^\s*{re.escape(RESEARCH_TITLE_MARKER)}(?:\s*[-:]\s*|\s+)?",
    flags=re.IGNORECASE,
)


def _normalize_whitespace(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _normalize_token(value: str) -> str:
    return _normalize_whitespace(re.sub(r"[^a-z0-9]+", " ", value))


def _is_status_changed_trigger(trigger: str) -> bool:
    return _normalize_token(trigger) == STATUS_CHANGED_TRIGGER


def _extract_status_name(value: Any) -> str | None:
    if isinstance(value, str):
        return value

    if isinstance(value, Mapping):
        name = value.get("name")
        if isinstance(name, str):
            return name

    return None


def add_research_marker(title: str, marker: str = RESEARCH_TITLE_MARKER) -> str:
    """Add the Cursor research marker to a title without duplicating it."""
    if TITLE_MARKER_PATTERN.match(title):
        return title

    clean_title = title.strip()
    if not clean_title:
        return marker

    return f"{marker} - {clean_title}"


def update_issue_title_for_status(title: str, new_status: str) -> str:
    """Return a marked title only when the issue moves to `to research`."""
    if _normalize_whitespace(new_status) == RESEARCH_STATUS_NAME:
        return add_research_marker(title)

    return title


def _extract_trigger_context(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    trigger_context = payload.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        return trigger_context

    return payload


def derive_updated_title(payload: Mapping[str, Any]) -> str | None:
    """Derive the title update for a Linear automation status-change payload."""
    trigger_context = _extract_trigger_context(payload)

    trigger = trigger_context.get("trigger")
    if isinstance(trigger, str) and not _is_status_changed_trigger(trigger):
        return None

    title = trigger_context.get("title")
    new_status = _extract_status_name(
        trigger_context.get("newStatus", trigger_context.get("status"))
    )
    if not isinstance(title, str) or new_status is None:
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
        description="Mark Linear issue titles when status changes to to research."
    )
    parser.add_argument(
        "--input",
        help="Path to input JSON payload. Reads from stdin when omitted.",
    )
    args = parser.parse_args(argv)

    payload = _load_payload(args.input)
    updated_title = derive_updated_title(payload)
    print(json.dumps({"updatedTitle": updated_title}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
