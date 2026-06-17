"""Build Linear issue title updates for research status transitions.

The automation layer supplies Linear webhook data in a few shapes.  This module
keeps the decision small and deterministic: when an issue status changes to
"to research", return an action that prefixes the title with "Cursor
researching".
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"

_EVENT_KEYS = ("trigger", "webhookType", "webhook_type", "action", "type", "event")
_STATUS_FIELD_NAMES = {"status", "state", "workflow state"}
_STATUS_VALUE_KEYS = (
    "newStatus",
    "new_status",
    "toStatus",
    "to_status",
    "newState",
    "new_state",
    "toState",
    "to_state",
    "newWorkflowState",
    "new_workflow_state",
    "toWorkflowState",
    "to_workflow_state",
    "status",
    "state",
    "workflowState",
    "workflow_state",
)
_ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "key", "id")


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update action when a Linear issue enters research status.

    The returned dictionary is intentionally side-effect free so callers can
    decide how to apply it through their Linear client.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_change_event(event, contexts):
        return None

    if not _has_target_status(contexts):
        return None

    issue_id = _first_text_value(contexts, _ISSUE_ID_KEYS)
    title = _first_text_value(contexts, ("title", "name"))
    if not issue_id or not title:
        return None

    stripped_title = title.strip()
    if not stripped_title or _has_title_prefix(stripped_title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {stripped_title}",
    }


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)

    add(event)
    for key in ("triggerContext", "trigger_context", "data", "issue"):
        add(event.get(key))

    for parent_key in ("triggerContext", "trigger_context", "data", "issue"):
        parent = event.get(parent_key)
        if isinstance(parent, Mapping):
            for child_key in ("issue", "data", "state", "workflowState", "workflow_state"):
                add(parent.get(child_key))

    return contexts


def _is_status_change_event(
    event: Mapping[str, Any], contexts: Iterable[Mapping[str, Any]]
) -> bool:
    event_names = {
        normalized
        for context in contexts
        for key in _EVENT_KEYS
        if (normalized := _normalize_text(context.get(key)))
    }

    if any(_names_status_change(name) for name in event_names):
        return True

    if any(name in {"update", "updated", "issue update", "issue updated"} for name in event_names):
        return _has_status_field_change(event)

    return False


def _names_status_change(name: str) -> bool:
    if name in {"status changed", "state changed", "workflow state changed"}:
        return True
    return "changed" in name and any(field in name.split() for field in ("status", "state"))


def _has_status_field_change(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized_key = _normalize_text(key)
            if normalized_key in {
                "updated fields",
                "changed fields",
                "changes",
                "updated from",
                "updated to",
            }:
                if _contains_status_field(child):
                    return True
            if _has_status_field_change(child):
                return True
    elif isinstance(value, list):
        return any(_has_status_field_change(item) for item in value)

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_text(value) in _STATUS_FIELD_NAMES

    if isinstance(value, Mapping):
        return any(
            _normalize_text(key) in _STATUS_FIELD_NAMES or _contains_status_field(child)
            for key, child in value.items()
        )

    if isinstance(value, list):
        return any(_contains_status_field(item) for item in value)

    return False


def _has_target_status(contexts: Iterable[Mapping[str, Any]]) -> bool:
    return any(
        _normalize_text(status_value) == TARGET_STATUS
        for context in contexts
        for status_value in _status_values_from_context(context)
    )


def _status_values_from_context(context: Mapping[str, Any]) -> Iterable[str]:
    for key in _STATUS_VALUE_KEYS:
        if key in context:
            yield from _status_value_texts(context[key])


def _status_value_texts(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, Mapping):
        for key in ("name", "title", "label", "newValue", "new_value", "to", "after"):
            if key in value:
                yield from _status_value_texts(value[key])


def _first_text_value(
    contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]
) -> str | None:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _has_title_prefix(title: str) -> bool:
    return bool(re.match(rf"^{re.escape(TITLE_PREFIX)}\b", title, re.IGNORECASE))


def _normalize_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    normalized = re.sub(r"[^A-Za-z0-9]+", " ", spaced).strip().lower()
    return re.sub(r"\s+", " ", normalized) if normalized else None


def main() -> int:
    event = json.load(sys.stdin)
    result = build_issue_title_update(event)
    if result is not None:
        print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
