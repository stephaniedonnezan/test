"""Build Linear issue title updates for research status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_NEW_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "toStatus",
    "to_status",
    "newState",
    "new_state",
    "stateName",
    "state_name",
    "workflowStateName",
    "workflow_state_name",
)
_STATUS_KEYS = ("status", "state", "workflowState", "workflow_state")
_ISSUE_ID_KEYS = ("issueId", "issue_id", "id", "identifier", "key")
_TITLE_KEYS = ("title", "name")
_STATUS_FIELD_NAMES = {"status", "state", "workflow state", "workflowstate"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title-update action when an issue moves to "to research".

    The automation runner provides Linear metadata in a few shapes, including a
    flat ``triggerContext`` object and nested webhook ``data.issue`` payloads.
    This function is side-effect free so callers can decide how to apply the
    returned action.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_change_event(contexts):
        return None

    if _normalize_status(_new_status(contexts)) != TARGET_STATUS:
        return None

    issue_id = _first_text(contexts, _ISSUE_ID_KEYS)
    title = _first_text(contexts, _TITLE_KEYS)
    if not issue_id or not title or _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)

    for parent_key in ("triggerContext", "trigger_context", "data"):
        parent = event.get(parent_key)
        if isinstance(parent, Mapping):
            add(parent.get("issue"))
            add(parent.get("data"))

    for key in ("triggerContext", "trigger_context", "data", "issue"):
        add(event.get(key))

    add(event)

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            add(issue.get("state"))
            add(issue.get("workflowState"))

    return contexts


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    context_list = list(contexts)
    event_values = []
    for context in context_list:
        for key in ("trigger", "webhookType", "webhook_type", "action", "type"):
            value = context.get(key)
            if isinstance(value, str):
                event_values.append(_normalize_words(value))

    if any("status changed" in value or "status change" in value for value in event_values):
        return True

    if any(value in {"update", "updated", "issue updated", "updated issue"} for value in event_values):
        return _has_status_update_marker(context_list)

    return False


def _has_status_update_marker(contexts: Iterable[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            if _contains_status_field(context.get(key)):
                return True

        changes = context.get("changes")
        if isinstance(changes, Mapping) and _contains_status_field(changes.keys()):
            return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_words(value) in _STATUS_FIELD_NAMES

    if isinstance(value, Mapping):
        return any(_contains_status_field(key) for key in value.keys())

    if isinstance(value, Iterable):
        return any(_contains_status_field(item) for item in value)

    return False


def _new_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    context_list = list(contexts)
    explicit_status = _first_status_text(context_list, _NEW_STATUS_KEYS)
    if explicit_status:
        return explicit_status

    changes_status = _changed_status(context_list)
    if changes_status:
        return changes_status

    return _first_status_text(context_list, _STATUS_KEYS)


def _changed_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        changes = context.get("changes")
        if not isinstance(changes, Mapping):
            continue

        for key, value in changes.items():
            if not _contains_status_field(key):
                continue

            if isinstance(value, Mapping):
                for nested_key in ("newValue", "new_value", "to", "after", "name"):
                    text = _text(value.get(nested_key))
                    if text:
                        return text
            else:
                text = _text(value)
                if text:
                    return text

    return None


def _first_status_text(contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if isinstance(value, Mapping):
                text = _first_text((value,), ("name", "title", "label"))
            else:
                text = _text(value)
            if text:
                return text
    return None


def _first_text(contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for context in contexts:
        for key in keys:
            text = _text(context.get(key))
            if text:
                return text
    return None


def _text(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _has_prefix(title: str) -> bool:
    return title.strip().lower().startswith(PREFIX.lower())


def _normalize_status(value: str | None) -> str | None:
    return _normalize_words(value) if value is not None else None


def _normalize_words(value: str) -> str:
    value = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    value = re.sub(r"[^A-Za-z0-9]+", " ", value)
    return " ".join(value.lower().split())


def main() -> None:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))


if __name__ == "__main__":
    main()
