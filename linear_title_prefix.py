"""Build Linear issue title updates for research status changes.

The automation runner can call ``build_issue_title_update`` with a Linear
webhook/automation payload. When an issue is moved into "to research", the
function returns a small action object instructing the caller to update the
issue title with the Cursor research prefix.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


RESEARCH_STATUS = "to research"
TITLE_PREFIX = "Cursor researching"
TITLE_PREFIX_WITH_SEPARATOR = f"{TITLE_PREFIX}: "

_STATUS_KEYS = ("status", "state", "workflowState")
_STATUS_CHANGE_FIELDS = frozenset({"status", "state", "workflowstate"})
_STATUS_CHANGE_TRIGGERS = frozenset(
    {
        "status changed",
        "status change",
        "state changed",
        "state change",
        "workflow state changed",
        "workflow state change",
    }
)
_ISSUE_UPDATE_TRIGGERS = frozenset(
    {
        "issue updated",
        "updated issue",
        "update issue",
        "update",
        "updated",
    }
)


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue-title update action for Linear research transitions.

    The returned action has the shape expected by this automation repository:
    ``{"action": "update_issue_title", "issueId": "...", "title": "..."}``.
    Non-status-change events, non-research statuses, missing issue data, and
    already-prefixed titles return ``None``.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_change(contexts):
        return None

    new_status = _new_status(contexts)
    if _normalize_label(new_status) != RESEARCH_STATUS:
        return None

    issue_id = _first_text(contexts, ("id", "issueId", "issue_id", "identifier"))
    title = _first_text(contexts, ("title", "name"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if not title or _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX_WITH_SEPARATOR}{title}",
    }


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return relevant payload mappings from most-specific to least-specific."""

    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)

    def collect(value: Any) -> None:
        if not isinstance(value, Mapping):
            return

        for key in ("issue", "data", "triggerContext", "trigger_context", "webhook"):
            collect(value.get(key))
        add(value)

    collect(event)

    return contexts


def _is_status_change(contexts: list[Mapping[str, Any]]) -> bool:
    metadata_values = _metadata_values(contexts)
    if any(value in _STATUS_CHANGE_TRIGGERS for value in metadata_values):
        return True

    is_issue_update = any(value in _ISSUE_UPDATE_TRIGGERS for value in metadata_values)
    return is_issue_update and _updated_fields_include_status(contexts)


def _metadata_values(contexts: list[Mapping[str, Any]]) -> set[str]:
    values: set[str] = set()
    for context in contexts:
        for key in ("trigger", "action", "type", "webhookType", "webhook_type"):
            value = context.get(key)
            if isinstance(value, str):
                values.add(_normalize_label(value))
    return values


def _updated_fields_include_status(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            fields = context.get(key)
            if isinstance(fields, str):
                if _normalize_field_name(fields) in _STATUS_CHANGE_FIELDS:
                    return True
            elif isinstance(fields, Mapping):
                if any(_normalize_field_name(str(field)) in _STATUS_CHANGE_FIELDS for field in fields):
                    return True
            elif isinstance(fields, list | tuple | set):
                if any(_normalize_field_name(str(field)) in _STATUS_CHANGE_FIELDS for field in fields):
                    return True
    return False


def _new_status(contexts: list[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        value = _text_status(context.get("newStatus"))
        if value:
            return value

        value = _text_status(context.get("new_status"))
        if value:
            return value

    for context in contexts:
        for key in _STATUS_KEYS:
            value = _text_status(context.get(key))
            if value:
                return value

    return None


def _text_status(value: Any) -> str | None:
    if isinstance(value, str):
        return value

    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            nested = value.get(key)
            if isinstance(nested, str):
                return nested

    return None


def _first_text(contexts: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def _normalize_field_name(value: str) -> str:
    return _normalize_label(value).replace(" ", "")


def _normalize_label(value: str | None) -> str | None:
    if value is None:
        return None

    with_spaces = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    with_spaces = re.sub(r"[^A-Za-z0-9]+", " ", with_spaces)
    return re.sub(r"\s+", " ", with_spaces).strip().lower()


def main() -> int:
    """Read a JSON event from stdin and print the generated action, if any."""

    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON input: {exc}", file=sys.stderr)
        return 1

    action = build_issue_title_update(payload)
    if action is not None:
        print(json.dumps(action, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
