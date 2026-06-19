"""Build Linear issue title updates for Cursor research handoffs.

The module is intentionally small and dependency-free so it can be used by a
Cursor automation step or invoked as a command line filter that reads webhook
JSON from stdin.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


TITLE_MARKER = "Cursor researching"
TITLE_PREFIX = f"{TITLE_MARKER}:"
TARGET_STATUS = "to research"

_STATUS_CHANGE_TRIGGERS = {
    "status changed",
    "status change",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
}

_STATUS_FIELDS = {
    "status",
    "state",
    "workflowstate",
    "workflow state",
    "workflow_state",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear issue title update action for "to research" transitions.

    The returned payload is a neutral action description:

        {
            "action": "update_issue_title",
            "issueId": "<issue id>",
            "title": "Cursor researching: <current title>",
        }

    ``None`` means no title change is needed.
    """

    if not isinstance(event, Mapping):
        return None

    context = _mapping_at(event, "triggerContext") or event

    if not _is_status_change(event, context):
        return None

    new_status = _new_status(event, context)
    if _normalize_phrase(new_status) != TARGET_STATUS:
        return None

    issue_id = _first_text(
        _value_at(context, "issueId"),
        _value_at(context, "issue.id"),
        _value_at(context, "id"),
        _value_at(event, "issueId"),
        _value_at(event, "issue.id"),
        _value_at(event, "data.id"),
        _value_at(event, "id"),
    )
    title = _first_text(
        _value_at(context, "title"),
        _value_at(context, "issue.title"),
        _value_at(context, "data.title"),
        _value_at(event, "title"),
        _value_at(event, "issue.title"),
        _value_at(event, "data.title"),
    )

    if issue_id is None or title is None:
        return None

    if _has_research_marker(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX} {title}",
    }


def main() -> int:
    """Read a JSON event from stdin and print the title update action or null."""

    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 2

    update = build_issue_title_update(event)
    print(json.dumps(update, sort_keys=True))
    return 0


def _is_status_change(event: Mapping[str, Any], context: Mapping[str, Any]) -> bool:
    trigger = _first_text(
        _value_at(context, "trigger"),
        _value_at(context, "triggerType"),
        _value_at(event, "trigger"),
        _value_at(event, "action"),
    )
    if _normalize_phrase(trigger) in _STATUS_CHANGE_TRIGGERS:
        return True

    if _first_text(_value_at(context, "newStatus"), _value_at(context, "new_status")):
        return True

    updated_from = _mapping_at(event, "updatedFrom") or _mapping_at(event, "updated_from")
    if updated_from is not None:
        return any(_is_status_field(key) for key in updated_from)

    return False


def _new_status(event: Mapping[str, Any], context: Mapping[str, Any]) -> str | None:
    """Extract the target status without reading old values from updatedFrom."""

    return _first_text(
        _value_at(context, "newStatus"),
        _value_at(context, "new_status"),
        _value_at(event, "newStatus"),
        _value_at(event, "new_status"),
        _value_at(context, "status"),
        _value_at(context, "state"),
        _value_at(context, "workflowState"),
        _value_at(context, "workflow_state"),
        _value_at(context, "data.status"),
        _value_at(context, "data.state"),
        _value_at(context, "data.workflowState"),
        _value_at(context, "data.workflow_state"),
        _value_at(context, "issue.status"),
        _value_at(context, "issue.state"),
        _value_at(context, "issue.workflowState"),
        _value_at(context, "issue.workflow_state"),
        _value_at(event, "data.status"),
        _value_at(event, "data.state"),
        _value_at(event, "data.workflowState"),
        _value_at(event, "data.workflow_state"),
        _value_at(event, "issue.status"),
        _value_at(event, "issue.state"),
        _value_at(event, "issue.workflowState"),
        _value_at(event, "issue.workflow_state"),
    )


def _value_at(data: Mapping[str, Any], path: str) -> Any:
    current: Any = data
    for part in path.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return None
        current = current[part]
    return current


def _mapping_at(data: Mapping[str, Any], path: str) -> Mapping[str, Any] | None:
    value = _value_at(data, path)
    return value if isinstance(value, Mapping) else None


def _first_text(*values: Any) -> str | None:
    for value in values:
        text = _coerce_text(value)
        if text is not None:
            return text
    return None


def _coerce_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    if isinstance(value, Mapping):
        return _first_text(
            value.get("name"),
            value.get("title"),
            value.get("label"),
            value.get("status"),
            value.get("state"),
            value.get("workflowState"),
            value.get("workflow_state"),
            value.get("value"),
        )
    return None


def _normalize_phrase(value: Any) -> str:
    text = _coerce_text(value)
    if text is None:
        return ""

    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[_\-/]+", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def _is_status_field(field_name: Any) -> bool:
    normalized = _normalize_phrase(str(field_name))
    normalized_compact = normalized.replace(" ", "")
    return normalized in _STATUS_FIELDS or normalized_compact in _STATUS_FIELDS


def _has_research_marker(title: str) -> bool:
    return _normalize_phrase(title).startswith(_normalize_phrase(TITLE_MARKER))


if __name__ == "__main__":
    raise SystemExit(main())
