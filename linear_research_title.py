"""Derive Linear issue title updates for research-status automations."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Mapping
from typing import Any

RESEARCH_TITLE_PREFIX = "Cursor researching"
RESEARCH_STATUS_NAME = "to research"
STATUS_CHANGED_TRIGGER = "status_changed"
ISSUE_WEBHOOK_TYPE = "issue"

PREFIX_PATTERN = re.compile(
    rf"^\s*{re.escape(RESEARCH_TITLE_PREFIX)}(?:\s*[-:]\s*|\s+)?",
    flags=re.IGNORECASE,
)


def _normalize_words(value: str) -> str:
    """Normalize user-facing labels such as Linear status names."""
    return " ".join(value.strip().lower().split())


def _normalize_token(value: str) -> str:
    """Normalize machine-ish trigger names across spaces, dashes, and underscores."""
    return "_".join(re.findall(r"[a-z0-9]+", value.lower()))


def _is_issue_status_change(trigger_context: Mapping[str, Any]) -> bool:
    """Return whether available event metadata describes an issue status change."""
    webhook_type = trigger_context.get("webhookType")
    if isinstance(webhook_type, str) and _normalize_token(webhook_type) != ISSUE_WEBHOOK_TYPE:
        return False

    trigger = trigger_context.get("trigger")
    if isinstance(trigger, str) and _normalize_token(trigger) != STATUS_CHANGED_TRIGGER:
        return False

    return True


def _prefixed_title(title: str) -> str:
    """Prefix a title while preserving already-prefixed titles exactly."""
    if PREFIX_PATTERN.match(title):
        return title

    clean_title = title.strip()
    if not clean_title:
        return RESEARCH_TITLE_PREFIX

    return f"{RESEARCH_TITLE_PREFIX}: {clean_title}"


def title_for_status_change(title: str, new_status: str) -> str:
    """Return the title to use after a Linear issue status change."""
    if _normalize_words(new_status) != RESEARCH_STATUS_NAME:
        return title

    return _prefixed_title(title)


def _trigger_context(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    trigger_context = payload.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        return trigger_context

    return payload


def derive_updated_title(payload: Mapping[str, Any]) -> str | None:
    """Return the new Linear title for a payload, or None when no update is needed."""
    trigger_context = _trigger_context(payload)
    if not _is_issue_status_change(trigger_context):
        return None

    title = trigger_context.get("title")
    new_status = trigger_context.get("newStatus")
    if not isinstance(title, str) or not isinstance(new_status, str):
        return None

    updated_title = title_for_status_change(title=title, new_status=new_status)
    if updated_title == title:
        return None

    return updated_title


def _load_payload(input_path: str | None) -> Mapping[str, Any]:
    if input_path is None:
        payload = json.load(sys.stdin)
    else:
        with open(input_path, encoding="utf-8") as input_file:
            payload = json.load(input_file)

    if not isinstance(payload, Mapping):
        raise ValueError("Linear automation payload must be a JSON object.")

    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Add the Cursor researching prefix for Linear issues moved to to research."
    )
    parser.add_argument(
        "--input",
        help="Read the Linear automation payload from this JSON file instead of stdin.",
    )
    args = parser.parse_args(argv)

    updated_title = derive_updated_title(_load_payload(args.input))
    print(json.dumps({"updatedTitle": updated_title}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
