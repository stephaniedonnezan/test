"""Build Linear issue title updates for research status transitions.

The automation that calls this module is responsible for applying the returned
action to Linear. This module keeps the decision deterministic and easy to test.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
TITLE_SEPARATOR = ": "

_STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}
_TRIGGER_KEYS = ("trigger", "webhookType", "action", "type", "eventType")
_DIRECT_STATUS_TRIGGERS = {
    "status change",
    "status changed",
    "status update",
    "status updated",
    "state change",
    "state changed",
    "workflow state change",
    "workflow state changed",
}
_GENERIC_UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return the title update action for a Linear status-change event.

    The action is only returned when an issue status transition lands on
    "to research" and the title does not already start with the configured
    prefix.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_change_event(contexts):
        return None

    status = _new_status(contexts)
    if _normalize(status) != TARGET_STATUS:
        return None

    issue_id = _first_text(contexts, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_text(contexts, ("title", "name"))
    if not issue_id or not title:
        return None

    if title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}{TITLE_SEPARATOR}{title}",
    }


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return payload layers in issue-first lookup order."""

    contexts: list[Mapping[str, Any]] = []

    trigger_context = _mapping_at(event, "triggerContext")
    data = _mapping_at(event, "data")
    issue = _mapping_at(event, "issue") or _mapping_at(data, "issue")

    for context in (trigger_context, issue, data, event):
        if context and context not in contexts:
            contexts.append(context)

    return contexts


def _mapping_at(mapping: Mapping[str, Any] | None, key: str) -> Mapping[str, Any] | None:
    if not isinstance(mapping, Mapping):
        return None
    value = mapping.get(key)
    return value if isinstance(value, Mapping) else None


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    trigger_values = [_normalize(context.get(key)) for context in contexts for key in _TRIGGER_KEYS]
    trigger_values = [value for value in trigger_values if value]

    if any(value in _DIRECT_STATUS_TRIGGERS for value in trigger_values):
        return True

    if any(value in _GENERIC_UPDATE_TRIGGERS for value in trigger_values):
        return _has_status_change_marker(contexts)

    # Some automation payloads provide only the changed status value.
    return bool(_new_status(contexts) and not trigger_values)


def _has_status_change_marker(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        updated_fields = context.get("updatedFields") or context.get("updated_fields")
        if _contains_status_field(updated_fields):
            return True

        changes = context.get("changes") or context.get("changedFields") or context.get("changed_fields")
        if isinstance(changes, Mapping) and any(_field_name_is_status(field) for field in changes):
            return True
        if _contains_status_field(changes):
            return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _field_name_is_status(value)
    if isinstance(value, Mapping):
        return any(_field_name_is_status(field) for field in value)
    if isinstance(value, list | tuple | set):
        return any(_contains_status_field(item) for item in value)
    return False


def _field_name_is_status(value: Any) -> bool:
    return _normalize_field(value) in _STATUS_FIELDS


def _new_status(contexts: list[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        status = _status_from_changes(context)
        if status:
            return status

    for context in contexts:
        for key in ("newStatus", "new_status", "toStatus", "to_status"):
            status = _text_from_status_value(context.get(key))
            if status:
                return status

    for context in contexts:
        for key in ("status", "state", "workflowState", "workflow_state"):
            status = _text_from_status_value(context.get(key))
            if status:
                return status

    return None


def _status_from_changes(context: Mapping[str, Any]) -> str | None:
    changes = context.get("changes") or context.get("changedFields") or context.get("changed_fields")
    if not isinstance(changes, Mapping):
        return None

    for field, change in changes.items():
        if not _field_name_is_status(field):
            continue

        if isinstance(change, Mapping):
            for key in ("to", "toValue", "newValue", "new", "after", "value", "name"):
                status = _text_from_status_value(change.get(key))
                if status:
                    return status
        else:
            status = _text_from_status_value(change)
            if status:
                return status

    return None


def _text_from_status_value(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "label", "displayName", "key", "id"):
            text = _text_from_status_value(value.get(key))
            if text:
                return text

    return None


def _first_text(contexts: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if isinstance(value, str):
                stripped = value.strip()
                if stripped:
                    return stripped
    return None


def _normalize(value: Any) -> str:
    text = _text_from_status_value(value)
    if not text:
        return ""
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def _normalize_field(value: Any) -> str:
    return _normalize(value).replace(" ", "")


def main() -> int:
    """Read a JSON event from stdin and print the computed action."""

    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 2

    action = build_issue_title_update(event)
    print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
