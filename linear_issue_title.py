#!/usr/bin/env python3
"""Apply Linear issue title updates for status-change automations."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Mapping
from typing import Any

RESEARCH_STATUS = "to research"
RESEARCH_TITLE_PREFIX = "Cursor researching"

_PREFIX_RE = re.compile(
    rf"^\s*{re.escape(RESEARCH_TITLE_PREFIX)}(?:\s*[-:]\s*|\s+)?",
    re.IGNORECASE,
)


def _normalize_words(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _normalize_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def _trigger_context(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    context = payload.get("triggerContext")
    if isinstance(context, Mapping):
        return context
    return payload


def _get_text(context: Mapping[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = context.get(key)
        if isinstance(value, str):
            return value
    return None


def _has_research_prefix(title: str) -> bool:
    return bool(_PREFIX_RE.match(title))


def prefix_research_title(title: str) -> str:
    """Return title with the research marker, without adding it twice."""
    if _has_research_prefix(title):
        return title

    stripped_title = title.strip()
    if not stripped_title:
        return RESEARCH_TITLE_PREFIX
    return f"{RESEARCH_TITLE_PREFIX} - {stripped_title}"


def title_for_status_change(payload: Mapping[str, Any]) -> str | None:
    """Return the updated title when a Linear issue moves to to research.

    The Cursor automation payload nests Linear details under ``triggerContext``.
    This function also accepts that same shape flattened at the top level for
    easier reuse and testing.
    """
    context = _trigger_context(payload)

    trigger = _get_text(context, "trigger")
    if trigger is not None and _normalize_token(trigger) != "status_changed":
        return None

    status = _get_text(context, "newStatus", "status")
    title = _get_text(context, "title")
    if status is None or title is None:
        return None

    if _normalize_words(status) != RESEARCH_STATUS:
        return None

    updated_title = prefix_research_title(title)
    if updated_title == title:
        return None
    return updated_title


def _read_payload(input_path: str | None) -> Mapping[str, Any]:
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
        description=(
            "Prefix a Linear issue title with 'Cursor researching' when the "
            "status changes to 'to research'."
        )
    )
    parser.add_argument(
        "--input",
        "-i",
        help="Path to a JSON payload file. Reads from stdin when omitted.",
    )
    args = parser.parse_args(argv)

    updated_title = title_for_status_change(_read_payload(args.input))
    print(json.dumps({"updatedTitle": updated_title}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
