"""Helpers for prefixing Linear issue titles during research handoff.

Cursor and Linear webhook payloads can be flat or nested. This module keeps the
decision deterministic: when a status-change event moves an issue to
"to research", return the issue-title update to apply.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear issue-title update action for research status changes."""

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    if _normalize(_status_name(event)) != TARGET_STATUS:
        return None

    issue_contexts = _issue_contexts(event)
    issue_id = _first_text(issue_contexts, ("id", "issueId", "issue_id", "identifier"))
    title = _first_text(issue_contexts, ("title", "name"))
    if issue_id is None or title is None:
        return None

    trimmed_title = title.strip()
    updated_title = (
        trimmed_title if _has_research_prefix(trimmed_title) else f"{TITLE_PREFIX}: {trimmed_title}"
    )

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": updated_title,
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    event_kinds = {_normalize(value) for value in _trigger_values(event)}

    status_change_kinds = {
        "status changed",
        "status change",
        "status updated",
        "state changed",
        "state change",
        "workflow state changed",
        "workflow state change",
    }
    if event_kinds & status_change_kinds:
        return True

    updated_fields = {_normalize(value) for value in _updated_fields(event)}
    has_status_field = bool(updated_fields & {"status", "state", "workflow state"})
    issue_update_kinds = {"issue updated", "updated issue", "update", "updated"}
    return has_status_field and bool(event_kinds & issue_update_kinds)


def _status_name(event: Mapping[str, Any]) -> str | None:
    explicit_status_keys = (
        "newStatus",
        "new_status",
        "newStatusName",
        "new_status_name",
        "newState",
        "new_state",
        "newWorkflowState",
        "new_workflow_state",
    )
    fallback_status_keys = ("status", "statusName", "state", "workflowState")

    status_contexts = _status_contexts(event)
    status = _first_status_text(status_contexts, explicit_status_keys)
    if status is not None:
        return status
    return _first_status_text(status_contexts, fallback_status_keys)


def _status_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []
    for key in ("triggerContext", "trigger_context", "context", "payload"):
        value = _get(event, key)
        if isinstance(value, Mapping):
            contexts.append(value)
    contexts.append(event)

    data = _get(event, "data")
    if isinstance(data, Mapping):
        contexts.append(data)
        issue = _get(data, "issue")
        if isinstance(issue, Mapping):
            contexts.append(issue)

    issue = _get(event, "issue")
    if isinstance(issue, Mapping):
        contexts.append(issue)

    return _dedupe_mappings(contexts)


def _issue_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []

    for parent_key in ("triggerContext", "trigger_context", "context", "payload"):
        parent = _get(event, parent_key)
        if isinstance(parent, Mapping):
            nested_issue = _get(parent, "issue")
            if isinstance(nested_issue, Mapping):
                contexts.append(nested_issue)
            contexts.append(parent)

    data = _get(event, "data")
    if isinstance(data, Mapping):
        issue = _get(data, "issue")
        if isinstance(issue, Mapping):
            contexts.append(issue)
        contexts.append(data)

    issue = _get(event, "issue")
    if isinstance(issue, Mapping):
        contexts.append(issue)

    contexts.append(event)
    return _dedupe_mappings(contexts)


def _trigger_values(event: Mapping[str, Any]) -> Iterable[Any]:
    trigger_keys = (
        "trigger",
        "webhookType",
        "webhook_type",
        "action",
        "type",
        "eventType",
        "event_type",
    )
    for context in _trigger_contexts(event):
        for key in trigger_keys:
            value = _get(context, key)
            if value is not None:
                yield value


def _trigger_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = [event]
    for key in ("triggerContext", "trigger_context", "context", "payload", "data"):
        value = _get(event, key)
        if isinstance(value, Mapping):
            contexts.append(value)
    return _dedupe_mappings(contexts)


def _updated_fields(event: Mapping[str, Any]) -> Iterable[Any]:
    field_keys = ("updatedFields", "updated_fields", "changedFields", "changed_fields")
    for context in _trigger_contexts(event) + _issue_contexts(event):
        for key in field_keys:
            value = _get(context, key)
            if isinstance(value, Mapping):
                yield from value.keys()
            elif isinstance(value, str):
                yield value
            elif isinstance(value, Iterable):
                yield from value

        changes = _get(context, "changes")
        if isinstance(changes, Mapping):
            yield from changes.keys()


def _first_status_text(contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for context in contexts:
        for key in keys:
            value = _get(context, key)
            if isinstance(value, Mapping):
                value = _get(value, "name")
            if isinstance(value, str) and value.strip():
                return value
    return None


def _first_text(contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for context in contexts:
        for key in keys:
            value = _get(context, key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _get(mapping: Mapping[str, Any], key: str) -> Any:
    if key in mapping:
        return mapping[key]

    normalized_key = _normalize_key(key)
    for existing_key, value in mapping.items():
        if isinstance(existing_key, str) and _normalize_key(existing_key) == normalized_key:
            return value
    return None


def _dedupe_mappings(mappings: Iterable[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    seen: set[int] = set()
    unique: list[Mapping[str, Any]] = []
    for mapping in mappings:
        identity = id(mapping)
        if identity not in seen:
            seen.add(identity)
            unique.append(mapping)
    return unique


def _has_research_prefix(title: str) -> bool:
    normalized_title = _normalize(title)
    normalized_prefix = _normalize(TITLE_PREFIX)
    return normalized_title == normalized_prefix or normalized_title.startswith(
        f"{normalized_prefix} "
    )


def _normalize(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def _normalize_key(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", value).lower()


def main() -> int:
    """Read a JSON event from stdin and print the title-update action, if any."""

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
