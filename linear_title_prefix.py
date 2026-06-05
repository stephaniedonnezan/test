"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any

RESEARCHING_PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"
UPDATE_ISSUE_TITLE_ACTION = "update_issue_title"

_PREFIX_PATTERN = re.compile(
    rf"^\s*{re.escape(RESEARCHING_PREFIX)}(?:\s*[-:|]\s*|\s+)?",
    flags=re.IGNORECASE,
)
_CAMEL_CASE_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_STATUS_FIELD_NAMES = {"status", "state", "workflow state", "workflow status"}
_STATUS_CHANGE_TOKENS = {
    "status changed",
    "status change",
    "status updated",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow status changed",
}


def _normalize_token(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    separated = _CAMEL_CASE_BOUNDARY.sub(" ", value)
    words = re.sub(r"[^A-Za-z0-9]+", " ", separated).strip().lower().split()
    return " ".join(words)


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _first_mapping(*values: Any) -> Mapping[str, Any]:
    for value in values:
        if isinstance(value, Mapping):
            return value
    return {}


def _iter_string_values(values: Iterable[Any]) -> Iterable[str]:
    for value in values:
        if isinstance(value, str):
            yield value


def _field_mentions_status(value: Any) -> bool:
    if isinstance(value, str):
        token = _normalize_token(value)
        return token in _STATUS_FIELD_NAMES

    if isinstance(value, Mapping):
        return any(_field_mentions_status(item) for item in value.keys())

    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        return any(_field_mentions_status(item) for item in value)

    return False


def _has_status_change_marker(context: Mapping[str, Any]) -> bool:
    trigger_values = _iter_string_values(
        context.get(key) for key in ("trigger", "action", "type", "webhookType")
    )
    normalized_triggers = {_normalize_token(value) for value in trigger_values}

    if any(token in _STATUS_CHANGE_TOKENS for token in normalized_triggers):
        return True

    if any(
        token in {"update", "updated", "issue updated", "updated issue"}
        for token in normalized_triggers
    ):
        return _field_mentions_status(context.get("updatedFields")) or _field_mentions_status(
            context.get("changes")
        )

    if normalized_triggers:
        return False

    return "newStatus" in context or "new_status" in context


def _extract_context(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    trigger_context = _as_mapping(payload.get("triggerContext"))
    data = _as_mapping(payload.get("data"))
    issue = _as_mapping(data.get("issue")) or _as_mapping(payload.get("issue"))

    if trigger_context:
        nested_issue = _as_mapping(trigger_context.get("issue"))
        nested_data_issue = _as_mapping(
            _as_mapping(trigger_context.get("data")).get("issue")
        )
        issue = _first_mapping(nested_issue, nested_data_issue, issue)
        return {**data, **payload, **issue, **trigger_context}

    return {**data, **payload, **issue}


def _extract_status_name(value: Any) -> str:
    if isinstance(value, Mapping):
        return _normalize_token(value.get("name") or value.get("title") or value.get("id"))
    return _normalize_token(value)


def _extract_new_status(context: Mapping[str, Any]) -> str:
    for key in (
        "newStatus",
        "new_status",
        "status",
        "state",
        "workflowState",
        "workflow_status",
    ):
        status = _extract_status_name(context.get(key))
        if status:
            return status
    return ""


def _extract_text(context: Mapping[str, Any], keys: Iterable[str]) -> str:
    for key in keys:
        value = context.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def prefix_researching_title(title: str) -> str:
    """Return title prefixed with Cursor's research marker exactly once."""
    clean_title = title.strip()
    if not clean_title:
        return RESEARCHING_PREFIX
    if _PREFIX_PATTERN.match(clean_title):
        return clean_title
    return f"{RESEARCHING_PREFIX}: {clean_title}"


def build_issue_title_update(payload: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when a status change enters research."""
    if not isinstance(payload, Mapping):
        return None

    context = _extract_context(payload)
    if not _has_status_change_marker(context):
        return None

    if _extract_new_status(context) != RESEARCH_STATUS:
        return None

    issue_id = _extract_text(context, ("issueId", "issue_id", "id", "identifier", "key"))
    title = _extract_text(context, ("title", "name"))
    if not issue_id or not title:
        return None

    updated_title = prefix_researching_title(title)
    if updated_title == title:
        return None

    return {
        "action": UPDATE_ISSUE_TITLE_ACTION,
        "issueId": issue_id,
        "title": updated_title,
    }


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
        description="Build a Linear title update when an issue moves to to research."
    )
    parser.add_argument(
        "--input",
        help="Read payload JSON from this file instead of stdin.",
    )
    args = parser.parse_args(argv)

    print(json.dumps(build_issue_title_update(_load_payload(args.input))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
