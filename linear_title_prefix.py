"""Build Linear issue-title update actions for research status transitions.

The automation runtime supplies webhook payloads in a few slightly different
shapes. This module keeps the policy small and deterministic: when an issue
status-change event moves to "to research", prefix its title with
"Cursor researching" unless that prefix is already present.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_CAMEL_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_SEPARATORS = re.compile(r"[^a-zA-Z0-9]+")


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return an issue-title update action for Linear transitions to research.

    The returned action is intentionally data-only so the caller can decide how
    to apply it to Linear:

    {
        "action": "update_issue_title",
        "issueId": "POI-123",
        "title": "Cursor researching: Existing title",
    }
    """

    if not isinstance(event, Mapping):
        return None

    contexts = list(_contexts(event))
    if not _is_status_change_event(contexts):
        return None

    if _normalize_status(_new_status(contexts)) != TARGET_STATUS:
        return None

    issue_contexts = list(_issue_contexts(event))
    issue_id = _first_text(issue_contexts, ("id", "issueId", "issue_id", "identifier", "key", "uuid"))
    title = _first_text(issue_contexts, ("title", "name"))

    if not issue_id or not title:
        return None

    clean_title = title.strip()
    if _has_prefix(clean_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {clean_title}",
    }


def _contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield event-like mappings from outermost to innermost."""

    yield event

    trigger_context = _mapping(event.get("triggerContext"))
    if trigger_context:
        yield trigger_context

    data = _mapping(event.get("data"))
    if data:
        yield data
        issue = _mapping(data.get("issue"))
        if issue:
            yield issue

    issue = _mapping(event.get("issue"))
    if issue:
        yield issue


def _issue_contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely issue mappings before generic webhook metadata."""

    trigger_context = _mapping(event.get("triggerContext"))
    if trigger_context:
        yield trigger_context

    data = _mapping(event.get("data"))
    if data:
        issue = _mapping(data.get("issue"))
        if issue:
            yield issue
        yield data

    issue = _mapping(event.get("issue"))
    if issue:
        yield issue

    yield event


def _mapping(value: Any) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    event_names = [
        _normalize_words(value)
        for context in contexts
        for key, value in context.items()
        if key in {"trigger", "webhookType", "webhook_type", "action", "type"}
        and isinstance(value, str)
    ]

    if any(name in {"status changed", "status change"} for name in event_names):
        return True

    if any(name in {"issue updated", "updated issue", "update", "updated"} for name in event_names):
        return _status_field_changed(contexts)

    return False


def _status_field_changed(contexts: Iterable[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            if _contains_status_field(context.get(key)):
                return True

        changes = _mapping(context.get("changes"))
        if changes and any(_is_status_field_name(key) for key in changes):
            return True

        updated_from = _mapping(context.get("updatedFrom"))
        if updated_from and any(_is_status_field_name(key) for key in updated_from):
            return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field_name(value)

    if isinstance(value, Iterable) and not isinstance(value, (str, bytes, Mapping)):
        return any(_contains_status_field(item) for item in value)

    if isinstance(value, Mapping):
        return any(_is_status_field_name(key) for key in value)

    return False


def _is_status_field_name(value: Any) -> bool:
    return _normalize_identifier(value) in {"status", "state", "workflowstate"}


def _new_status(contexts: Iterable[Mapping[str, Any]]) -> Any:
    for context in contexts:
        for key in ("newStatus", "new_status", "statusName", "status_name", "stateName", "state_name"):
            if key in context:
                return _named_value(context[key])

    for context in contexts:
        for key in ("status", "state", "workflowState", "workflow_state"):
            if key in context:
                return _named_value(context[key])

    return None


def _named_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            if key in value:
                return value[key]
    return value


def _first_text(contexts: Iterable[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _has_prefix(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())


def _normalize_status(value: Any) -> str:
    return _normalize_words(value)


def _normalize_identifier(value: Any) -> str:
    normalized = _normalize_words(value)
    return normalized.replace(" ", "")


def _normalize_words(value: Any) -> str:
    if value is None:
        return ""
    text = _CAMEL_BOUNDARY.sub(" ", str(value))
    text = _SEPARATORS.sub(" ", text)
    return " ".join(text.casefold().split())


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is None:
        return 0

    json.dump(action, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
