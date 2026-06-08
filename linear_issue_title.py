"""Helpers for updating Linear issue titles from status-change payloads."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Mapping
from typing import Any

RESEARCHING_PREFIX = "Cursor researching"
TO_RESEARCH_STATUS = "to research"
_NORMALIZED_STATUS_CHANGED_TRIGGER = "status changed"

_RESEARCHING_PREFIX_PATTERN = re.compile(
    rf"^\s*{re.escape(RESEARCHING_PREFIX)}(?:\s*[-:|]\s*|\s+)?",
    re.IGNORECASE,
)


def _normalize_words(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _normalize_token(value: str) -> str:
    return _normalize_words(re.sub(r"[^a-z0-9]+", " ", value.lower()))


def _trigger_context(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    context = payload.get("triggerContext")
    if isinstance(context, Mapping):
        return context
    return payload


def with_researching_prefix(title: str) -> str:
    """Return title with a single `Cursor researching` prefix."""
    clean_title = title.strip()
    if not clean_title:
        return RESEARCHING_PREFIX

    if _RESEARCHING_PREFIX_PATTERN.match(clean_title):
        return clean_title

    return f"{RESEARCHING_PREFIX} - {clean_title}"


def updated_title_for_status_change(payload: Mapping[str, Any]) -> str | None:
    """Return the updated Linear issue title, or None when no change is needed."""
    context = _trigger_context(payload)

    trigger = context.get("trigger")
    if (
        isinstance(trigger, str)
        and _normalize_token(trigger) != _NORMALIZED_STATUS_CHANGED_TRIGGER
    ):
        return None

    status = context.get("newStatus", context.get("status"))
    if not isinstance(status, str) or _normalize_words(status) != TO_RESEARCH_STATUS:
        return None

    title = context.get("title")
    if not isinstance(title, str):
        return None

    next_title = with_researching_prefix(title)
    if next_title == title:
        return None
    return next_title


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
        description=(
            "Add the Cursor researching prefix when a Linear issue moves to "
            "to research."
        )
    )
    parser.add_argument(
        "--input",
        help="Path to input JSON payload. Reads from stdin when omitted.",
    )
    args = parser.parse_args(argv)

    updated_title = updated_title_for_status_change(_load_payload(args.input))
    print(json.dumps({"updatedTitle": updated_title}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
