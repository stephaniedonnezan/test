"""Build Linear issue title updates for Cursor research automations.

The automation receives Linear status-change events in a few shapes. This
module keeps the trigger decision small and deterministic: when an issue moves
to "to research", prefix its title with "Cursor researching" exactly once.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow state"}
UPDATE_TRIGGERS = {"update", "updated", "issue update", "issue updated", "updated issue"}
STATUS_CHANGE_TRIGGERS = {
    "status change",
    "status changed",
    "state change",
    "state changed",
    "workflow state change",
    "workflow state changed",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear issue title update action for matching research events.

    The return value is intentionally serializable so callers can hand it to the
    surrounding automation layer:

    {
        "action": "update_issue_title",
        "issueId": "POI-123",
        "title": "Cursor researching: Original title",
    }
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _event_contexts(event)
    if not _is_status_change_event(contexts):
        return None

    status = _changed_status(contexts)
    if _normalize_text(status) != TARGET_STATUS:
        return None

    issue_id = _first_text(contexts, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_text(contexts, ("title", "name"))
    if not issue_id or not title:
        return None

    if title.lower().startswith(PREFIX.lower()):
        updated_title = title
    else:
        updated_title = f"{PREFIX}: {title}"

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": updated_title,
    }


def _event_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Collect likely payload locations ordered from outer metadata to issue data."""

    contexts: list[Mapping[str, Any]] = [event]

    for path in (
        ("triggerContext",),
        ("data",),
        ("issue",),
        ("data", "issue"),
        ("data", "state"),
        ("data", "workflowState"),
        ("triggerContext", "data"),
        ("triggerContext", "issue"),
        ("triggerContext", "data", "issue"),
    ):
        value = _get_path(event, path)
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)

    return contexts


def _is_status_change_event(contexts: Sequence[Mapping[str, Any]]) -> bool:
    trigger_values = [
        _normalize_text(value)
        for context in contexts
        for key in ("trigger", "webhookType", "action", "type", "eventType")
        if (value := context.get(key)) is not None
    ]

    if any(value in STATUS_CHANGE_TRIGGERS for value in trigger_values):
        return True

    if any(value in UPDATE_TRIGGERS for value in trigger_values):
        return _has_status_field_change(contexts)

    return False


def _has_status_field_change(contexts: Sequence[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "changedFields", "fields"):
            if _contains_status_field(context.get(key)):
                return True

        changes = context.get("changes")
        if _contains_status_field(changes):
            return True

        updated_from = context.get("updatedFrom")
        if _contains_status_field(updated_from):
            return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_field_name(value) in STATUS_FIELD_NAMES

    if isinstance(value, Mapping):
        return any(_contains_status_field(key) for key in value.keys())

    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        return any(_contains_status_field(item) for item in value)

    return False


def _changed_status(contexts: Sequence[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        status = _first_text(
            [context],
            (
                "newStatus",
                "new_status",
                "statusName",
                "stateName",
                "workflowStateName",
            ),
        )
        if status:
            return status

    for context in contexts:
        status = _status_from_changes(context)
        if status:
            return status

    for context in contexts:
        for key in ("status", "state", "workflowState"):
            status = _text_or_named_value(context.get(key))
            if status:
                return status

    return None


def _status_from_changes(context: Mapping[str, Any]) -> str | None:
    changes = context.get("changes")
    if not isinstance(changes, Mapping):
        return None

    for key, value in changes.items():
        if _normalize_field_name(key) not in STATUS_FIELD_NAMES:
            continue

        status = _text_or_named_value(value)
        if status:
            return status

        if isinstance(value, Mapping):
            for status_key in ("newValue", "new_value", "to", "after", "name"):
                status = _text_or_named_value(value.get(status_key))
                if status:
                    return status

    return None


def _first_text(contexts: Sequence[Mapping[str, Any]], keys: Sequence[str]) -> str | None:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _text_or_named_value(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()

    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            nested = value.get(key)
            if isinstance(nested, str) and nested.strip():
                return nested.strip()

    return None


def _get_path(source: Mapping[str, Any], path: Sequence[str]) -> Any:
    current: Any = source
    for key in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current


def _normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    words = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value.strip())
    words = re.sub(r"[_\-.]+", " ", words)
    words = re.sub(r"\s+", " ", words)
    return words.casefold()


def _normalize_field_name(value: Any) -> str:
    return _normalize_text(value).replace(" ", "")


def main() -> int:
    """Read an event JSON payload from stdin and print the requested action."""

    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    action = build_issue_title_update(payload)
    if action is None:
        return 0

    print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
