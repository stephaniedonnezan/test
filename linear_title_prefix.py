"""Build Linear issue title updates for research-status automations.

The module is intentionally dependency-free so it can run in a small Cursor
automation environment. It accepts either the flattened Cursor trigger context
or common nested Linear webhook payload shapes and returns a normalized action
for callers to apply through their Linear client.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


RESEARCH_STATUS = "to research"
TITLE_PREFIX = "Cursor researching"

_STATUS_FIELDS = ("status", "state", "workflowState", "workflow_state")
_NEW_STATUS_FIELDS = (
    "newStatus",
    "new_status",
    "toStatus",
    "to_status",
    "status",
    "state",
    "workflowState",
    "workflow_state",
)
_TRIGGER_FIELDS = ("trigger", "webhookType", "webhook_type", "action", "type")
_STATUS_CHANGE_MARKERS = ("status", "state", "workflowstate", "workflow_state")


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return an issue-title update action when a Linear issue enters research.

    The returned action is side-effect free:
    ``{"action": "update_issue_title", "issueId": "...", "title": "..."}``.
    Callers can submit it to Linear if desired. Non-matching or incomplete
    payloads return ``None``.
    """

    if not isinstance(event, Mapping):
        return None

    context = _flatten_event_context(event)
    if not _is_status_change_event(context):
        return None

    new_status = _extract_new_status(context)
    if _normalize_token(new_status) != _normalize_token(RESEARCH_STATUS):
        return None

    title = _string_value(_first_present(context, ("title", "name")))
    issue_id = _string_value(
        _first_present(context, ("issueId", "issue_id", "identifier", "key", "id"))
    )
    if not title or not issue_id:
        return None

    cleaned_title = title.strip()
    if _has_research_prefix(cleaned_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {cleaned_title}",
    }


def _flatten_event_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge useful nested payload sections into one lookup dictionary."""

    context: dict[str, Any] = {}

    def merge(value: Any) -> None:
        if isinstance(value, Mapping):
            context.update(value)

    data = event.get("data")
    trigger_context = event.get("triggerContext")
    issue = event.get("issue")

    if isinstance(data, Mapping):
        merge(data.get("issue"))
        merge(data.get("entity"))
        merge(data)

    merge(issue)
    merge(trigger_context)
    merge(event)

    # Keep nested issue fields authoritative for the issue title/id even when
    # the top-level payload only provides generic event metadata.
    if isinstance(data, Mapping):
        _copy_missing_issue_fields(context, data.get("issue"))
    _copy_missing_issue_fields(context, issue)

    return context


def _copy_missing_issue_fields(context: dict[str, Any], issue: Any) -> None:
    if not isinstance(issue, Mapping):
        return

    for key in ("title", "name", "issueId", "issue_id", "identifier", "key", "id"):
        if key not in context and key in issue:
            context[key] = issue[key]


def _is_status_change_event(context: Mapping[str, Any]) -> bool:
    trigger_values = [
        _normalize_token(value)
        for key in _TRIGGER_FIELDS
        for value in _values_for_key(context, key)
        if value is not None
    ]

    if any("statuschanged" in value or "statuschange" in value for value in trigger_values):
        return True

    if any("issueupdated" in value or value == "update" for value in trigger_values):
        return _has_status_change_marker(context)

    return False


def _has_status_change_marker(context: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields"):
        if _sequence_contains_status_marker(context.get(key)):
            return True

    for key in ("changes", "updatedFrom", "updated_from"):
        changes = context.get(key)
        if isinstance(changes, Mapping):
            if any(_is_status_marker(field) for field in changes):
                return True
        elif _sequence_contains_status_marker(changes):
            return True

    return False


def _sequence_contains_status_marker(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_marker(value)
    if isinstance(value, Mapping):
        return any(_is_status_marker(key) for key in value)
    if isinstance(value, list | tuple | set):
        return any(_sequence_contains_status_marker(item) for item in value)
    return False


def _is_status_marker(value: Any) -> bool:
    normalized = _normalize_token(value)
    return normalized in _STATUS_CHANGE_MARKERS


def _extract_new_status(context: Mapping[str, Any]) -> str | None:
    for key in _NEW_STATUS_FIELDS:
        for value in _values_for_key(context, key):
            status = _status_name(value)
            if status:
                return status

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        for field in _STATUS_FIELDS:
            if field in changes:
                status = _status_name(_new_value(changes[field]))
                if status:
                    return status

    return None


def _new_value(value: Any) -> Any:
    if not isinstance(value, Mapping):
        return value
    for key in ("to", "new", "after", "value", "name"):
        if key in value:
            return value[key]
    return value


def _status_name(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("name", "title", "status", "state", "workflowState"):
            status = _status_name(value.get(key))
            if status:
                return status
        return None

    return _string_value(value)


def _values_for_key(context: Mapping[str, Any], key: str) -> list[Any]:
    values: list[Any] = []
    if key in context:
        values.append(context[key])

    snake_key = _camel_to_snake(key)
    if snake_key != key and snake_key in context:
        values.append(context[snake_key])

    return values


def _first_present(context: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in context:
            return context[key]
    return None


def _string_value(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def _normalize_token(value: Any) -> str:
    text = _string_value(value)
    if not text:
        return ""
    text = _camel_to_words(text)
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def _camel_to_words(value: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)


def _camel_to_snake(value: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", value).lower()


def main() -> int:
    """Read a JSON event from stdin and print the computed action."""

    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
