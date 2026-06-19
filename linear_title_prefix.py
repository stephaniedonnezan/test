"""Build Linear issue title updates for research status transitions."""

from __future__ import annotations

import argparse
from collections.abc import Mapping
import json
import re
import sys
from typing import Any


CURSOR_RESEARCHING_PREFIX = "Cursor researching"
RESEARCH_TITLE_PREFIX = CURSOR_RESEARCHING_PREFIX
UPDATE_ISSUE_TITLE_ACTION = "update_issue_title"
RESEARCH_STATUS = "to research"
STATUS_CHANGED_TRIGGER = "status changed"

_PREFIX_PATTERN = re.compile(
    rf"^\s*{re.escape(CURSOR_RESEARCHING_PREFIX)}(?:\s*[:\-]\s*|\s+|$)",
    flags=re.IGNORECASE,
)


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear issue-title update action when status changes to research."""
    context = _event_context(event)
    issue_id = _issue_id(context)
    updated_title = derive_updated_title(event)
    if not issue_id or updated_title is None:
        return None

    return {
        "action": UPDATE_ISSUE_TITLE_ACTION,
        "issueId": issue_id,
        "title": updated_title,
    }


def derive_updated_title(event: Mapping[str, Any]) -> str | None:
    """Return only the updated title for callers that do not need action metadata."""
    context = _event_context(event)
    if not context or not _is_status_changed(context):
        return None

    if _normalize_status(_new_status(context)) != RESEARCH_STATUS:
        return None

    title = _string_value(context.get("title"))
    if not title.strip():
        return None

    updated_title = _prefixed_title(title)
    return None if updated_title == title else updated_title


def update_issue_title_for_status(title: str, new_status: str) -> str:
    """Prefix ``title`` when ``new_status`` is Linear's to-research status."""
    if _normalize_status(new_status) != RESEARCH_STATUS:
        return title
    return _prefixed_title(title)


def _event_context(event: Mapping[str, Any]) -> Mapping[str, Any]:
    if not isinstance(event, Mapping):
        return {}
    return _trigger_context(event)


def _trigger_context(event: Mapping[str, Any]) -> Mapping[str, Any]:
    context = event.get("triggerContext")
    if isinstance(context, Mapping):
        return context
    return event


def _is_status_changed(context: Mapping[str, Any]) -> bool:
    trigger = _string_value(context.get("trigger"))
    webhook_type = _string_value(context.get("webhookType"))
    return (
        _normalize_token(trigger) == STATUS_CHANGED_TRIGGER
        or _normalize_token(webhook_type) == STATUS_CHANGED_TRIGGER
    )


def _new_status(context: Mapping[str, Any]) -> Any:
    for key in ("newStatus", "status"):
        value = context.get(key)
        if value:
            return value

    for key in ("newState", "state"):
        value = context.get(key)
        if isinstance(value, Mapping):
            return value.get("name")

    return None


def _issue_id(context: Mapping[str, Any]) -> str:
    issue_id = _string_value(context.get("id") or context.get("issueId"))
    if issue_id:
        return issue_id

    issue = context.get("issue")
    if isinstance(issue, Mapping):
        return _string_value(issue.get("id") or issue.get("identifier"))

    return ""


def _prefixed_title(title: str) -> str:
    if _PREFIX_PATTERN.match(title):
        return title
    return f"{CURSOR_RESEARCHING_PREFIX}: {title.strip()}"


def _normalize_token(value: Any) -> str:
    text = _string_value(value)
    if not text:
        return ""
    return _normalize_whitespace(_split_camel_case(text))


def _normalize_status(value: Any) -> str:
    text = _string_value(value)
    if not text:
        return ""
    return _normalize_whitespace(text)


def _normalize_whitespace(value: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value.lower()).split())


def _split_camel_case(value: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)


def _string_value(value: Any) -> str:
    return value if isinstance(value, str) else ""


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
        description="Build a Linear title update when an issue moves to to research.",
    )
    parser.add_argument(
        "--input",
        help="Path to a JSON payload. Reads from stdin when omitted.",
    )
    args = parser.parse_args(argv)

    print(json.dumps(build_issue_title_update(_load_payload(args.input))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
