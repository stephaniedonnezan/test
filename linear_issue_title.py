"""Add a research prefix to Linear issue titles for research status changes."""

from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any

RESEARCH_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
TARGET_TRIGGER = "status_changed"

_PREFIX_PATTERN = re.compile(
    rf"^\s*{re.escape(RESEARCH_PREFIX)}(?:\s*[-:]\s*|\s+)?",
    flags=re.IGNORECASE,
)


def _normalize_whitespace(value: str) -> str:
    return " ".join(value.split())


def _normalize_status(value: str) -> str:
    return _normalize_whitespace(value.strip().lower())


def _normalize_trigger(value: str) -> str:
    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    while "__" in normalized:
        normalized = normalized.replace("__", "_")
    return normalized


def extract_trigger_context(payload: dict[str, Any]) -> dict[str, Any]:
    """Return triggerContext for wrapped payloads, otherwise the payload itself."""
    trigger_context = payload.get("triggerContext")
    if isinstance(trigger_context, dict):
        return trigger_context
    return payload


def should_prefix_title(context: dict[str, Any]) -> bool:
    """Return True when payload represents issue status change to `to research`."""
    if str(context.get("webhookType", "")).strip().lower() != "issue":
        return False

    trigger = _normalize_trigger(str(context.get("trigger", "")))
    if trigger != TARGET_TRIGGER:
        return False

    new_status = str(context.get("newStatus", "")).strip()
    if not new_status:
        new_status = str(context.get("status", "")).strip()
    return _normalize_status(new_status) == TARGET_STATUS


def add_research_prefix(title: str) -> str:
    """Add `Cursor researching` prefix while avoiding duplicate prefixes."""
    compact_title = title.strip()
    if _PREFIX_PATTERN.match(compact_title):
        return compact_title
    if not compact_title:
        return RESEARCH_PREFIX
    return f"{RESEARCH_PREFIX} - {compact_title}"


def derive_updated_title(payload: dict[str, Any]) -> str | None:
    """Return updated title when payload should be prefixed; otherwise None."""
    context = extract_trigger_context(payload)
    if not isinstance(context, dict):
        return None

    title = context.get("title")
    if not isinstance(title, str):
        return None

    if not should_prefix_title(context):
        return None

    updated_title = add_research_prefix(title)
    if updated_title == title:
        return None
    return updated_title


def _load_payload(args: argparse.Namespace) -> dict[str, Any]:
    if args.input:
        with open(args.input, "r", encoding="utf-8") as input_file:
            return json.load(input_file)
    if not sys.stdin.isatty():
        return json.load(sys.stdin)
    raise ValueError("No payload source provided. Pass --input or pipe JSON to stdin.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", help="Path to payload JSON file.")
    args = parser.parse_args()

    try:
        payload = _load_payload(args)
        updated_title = derive_updated_title(payload)
    except Exception as exc:  # malformed payloads should fail clearly in logs
        print(f"Failed to process payload: {exc}", file=sys.stderr)
        return 2

    result = {"updatedTitle": updated_title}
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
