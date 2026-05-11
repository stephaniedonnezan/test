"""Build title updates for Linear issues entering research.

The automation runtime calls ``build_issue_title_update`` with the Linear
webhook payload.  When the issue status changes to "to research", it returns
an action instructing the runtime to prefix the issue title.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELDS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "status",
    "state",
    "workflowState",
    "workflow_state",
)
_TITLE_FIELDS = ("title", "name")
_ISSUE_ID_FIELDS = ("id", "issueId", "issue_id", "identifier")
_EVENT_TYPE_FIELDS = ("trigger", "webhookType", "webhook_type", "action", "type")
_UPDATED_FIELDS = ("updatedFields", "updated_fields", "changedFields", "changed_fields")
_NESTED_CONTEXT_FIELDS = ("triggerContext", "payload", "data", "issue")


def build_issue_title_update(event: Any) -> dict[str, str] | None:
    """Return a Linear title update action, or ``None`` when not applicable."""

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    status = _find_status(event)
    if _normalize_text(status) != TARGET_STATUS:
        return None

    issue_id = _find_first_text(event, _ISSUE_ID_FIELDS)
    title = _find_first_text(event, _TITLE_FIELDS)
    if issue_id is None or title is None:
        return None

    title = title.strip()
    if not title:
        return None

    prefixed_title = title if _has_prefix(title) else f"{PREFIX}: {title}"
    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": prefixed_title,
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    event_types = {
        _normalize_text(value)
        for value in _collect_values(event, _EVENT_TYPE_FIELDS)
        if _normalize_text(value)
    }

    if event_types & {
        "status changed",
        "status change",
        "statuschanged",
        "state changed",
        "workflow state changed",
    }:
        return True

    issue_updated = bool(
        event_types
        & {
            "issue updated",
            "updated issue",
            "update",
            "updated",
        }
    )
    if not issue_updated:
        return False

    updated_fields = {
        _normalize_text(value)
        for value in _collect_updated_field_values(event)
        if _normalize_text(value)
    }
    return bool(updated_fields & {"status", "state", "workflow state", "workflowstate"})


def _find_status(event: Mapping[str, Any]) -> str | None:
    for context in _candidate_contexts(event):
        for key in _STATUS_FIELDS:
            value = context.get(key)
            text = _status_text(value)
            if text is not None:
                return text
    return None


def _find_first_text(event: Mapping[str, Any], fields: tuple[str, ...]) -> str | None:
    for context in _candidate_contexts(event):
        for key in fields:
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value
            if not isinstance(value, (Mapping, list, tuple)) and value is not None:
                text = str(value).strip()
                if text:
                    return text
    return None


def _candidate_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return payload objects from most-specific/outermost to least-specific."""

    contexts: list[Mapping[str, Any]] = []
    seen: set[int] = set()

    def visit(value: Any) -> None:
        if not isinstance(value, Mapping):
            return
        identity = id(value)
        if identity in seen:
            return
        seen.add(identity)
        contexts.append(value)
        for key in _NESTED_CONTEXT_FIELDS:
            nested = value.get(key)
            if isinstance(nested, Mapping):
                visit(nested)

    visit(event)
    return contexts


def _status_text(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value
    if isinstance(value, Mapping):
        for key in ("name", "title", "status", "state", "workflowState"):
            text = _status_text(value.get(key))
            if text is not None:
                return text
    return None


def _collect_values(value: Any, fields: tuple[str, ...]) -> list[Any]:
    values: list[Any] = []

    def visit(current: Any) -> None:
        if isinstance(current, Mapping):
            for key, nested in current.items():
                if key in fields:
                    values.append(nested)
                visit(nested)
        elif isinstance(current, (list, tuple)):
            for item in current:
                visit(item)

    visit(value)
    return values


def _collect_updated_field_values(event: Mapping[str, Any]) -> list[Any]:
    values: list[Any] = []
    for updated_fields in _collect_values(event, _UPDATED_FIELDS):
        if isinstance(updated_fields, str):
            values.append(updated_fields)
        elif isinstance(updated_fields, Mapping):
            values.extend(updated_fields.keys())
            values.extend(updated_fields.values())
        elif isinstance(updated_fields, (list, tuple, set)):
            values.extend(updated_fields)
    return values


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def _has_prefix(title: str) -> bool:
    return title.strip().lower().startswith(PREFIX.lower())


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as error:
        print(f"Invalid JSON: {error}", file=sys.stderr)
        return 1

    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
