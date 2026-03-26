#!/usr/bin/env python3
"""Update Linear issue titles based on status transitions."""

from __future__ import annotations

import argparse
import json
from typing import Any

RESEARCH_PREFIX = "Cursor researching"


def _normalize(text: str) -> str:
    return text.strip().casefold()


def should_add_research_prefix(status: str | None) -> bool:
    """Return True when the provided status means 'To Research'."""
    return _normalize(status or "") == "to research"


def add_research_prefix(title: str, prefix: str = RESEARCH_PREFIX) -> str:
    """Prefix a title with the research marker (idempotent)."""
    stripped_title = title.lstrip()
    normalized_title = stripped_title.casefold()
    normalized_prefix = prefix.casefold()
    bracketed_prefix = f"[{normalized_prefix}]"

    if normalized_title.startswith(normalized_prefix) or normalized_title.startswith(
        bracketed_prefix
    ):
        return title

    if not title:
        return prefix

    return f"{prefix}: {title}"


def compute_title_from_trigger(payload: dict[str, Any]) -> tuple[str, bool]:
    """
    Compute updated title from a Linear webhook-like payload.

    Returns a tuple (title, changed).
    """
    trigger_context = payload.get("triggerContext", payload)
    current_title = str(trigger_context.get("title", ""))
    next_status = trigger_context.get("newStatus") or trigger_context.get("status")

    if not should_add_research_prefix(str(next_status or "")):
        return current_title, False

    updated_title = add_research_prefix(current_title)
    return updated_title, updated_title != current_title


def _read_payload(path: str | None) -> dict[str, Any]:
    raw = open(path, "r", encoding="utf-8").read() if path else input()
    return json.loads(raw)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Add 'Cursor researching' to issue title when status is To Research."
    )
    parser.add_argument(
        "--input",
        help="Path to JSON payload file. If omitted, payload is read from stdin.",
    )
    args = parser.parse_args()

    payload = _read_payload(args.input)
    title, changed = compute_title_from_trigger(payload)
    print(json.dumps({"title": title, "changed": changed}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
