"""Build Linear issue title updates for research status changes.

The automation runner can pass either a flat Cursor trigger context or a
nested Linear webhook payload.  This module keeps the behavior small and
side-effect free: callers receive the issue-title update they should perform,
or ``None`` when the event is not relevant.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_DIRECT_STATUS_CHANGE_EVENTS = {
    "status changed",
    "status change",
    "statuschanged",
}
_GENERIC_UPDATE_EVENTS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}
_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflow state",
    "workflowstate",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action for "to research" status changes.

    The returned action is intentionally serializable so it can be handed to
    whichever integration layer performs the Linear API call.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _candidate_contexts(event)
    if not _is_status_change_event(contexts):
        return None

    status = _new_status(contexts)
    if _normalize_text(status) != TARGET_STATUS:
        return None

    title = _first_text(contexts, ("title", "name"))
    issue_id = _first_text(
        contexts,
        ("issueId", "issue_id", "identifier", "key", "id"),
    )
    if not title or not issue_id:
        return None

    title = title.strip()
    if title.lower().startswith(TITLE_PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _candidate_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return likely metadata and issue containers in priority order."""

    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        add(trigger_context.get("issue"))
        trigger_data = trigger_context.get("data")
        if isinstance(trigger_data, Mapping):
            add(trigger_data.get("issue"))
            add(trigger_data)
        add(trigger_context)

    data = event.get("data")
    if isinstance(data, Mapping):
        add(data.get("issue"))
        add(data)

    add(event.get("issue"))
    add(event)

    return contexts


def _is_status_change_event(contexts: Sequence[Mapping[str, Any]]) -> bool:
    event_names = {
        _normalize_text(value)
        for context in contexts
        for key in ("trigger", "webhookType", "webhook_type", "action", "type", "eventType")
        for value in (context.get(key),)
        if isinstance(value, str)
    }

    if event_names & _DIRECT_STATUS_CHANGE_EVENTS:
        return True

    if event_names & _GENERIC_UPDATE_EVENTS:
        return _has_status_field_change(contexts)

    return False


def _has_status_field_change(contexts: Sequence[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            if _contains_status_field(context.get(key)):
                return True

        changes = context.get("changes")
        if isinstance(changes, Mapping):
            if any(_is_status_field(field) for field in changes):
                return True
        elif _contains_status_field(changes):
            return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)

    if isinstance(value, Mapping):
        for key in ("field", "fieldName", "name", "key"):
            if _is_status_field(value.get(key)):
                return True
        return any(_contains_status_field(item) for item in value.values())

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return any(_contains_status_field(item) for item in value)

    return False


def _is_status_field(value: Any) -> bool:
    return isinstance(value, str) and _normalize_text(value) in _STATUS_FIELD_NAMES


def _new_status(contexts: Sequence[Mapping[str, Any]]) -> str | None:
    explicit_status = _first_text(
        contexts,
        (
            "newStatus",
            "new_status",
            "newState",
            "new_state",
            "newWorkflowState",
            "new_workflow_state",
            "toStatus",
            "to_status",
            "toState",
            "to_state",
            "statusName",
            "status_name",
        ),
    )
    if explicit_status:
        return explicit_status

    changed_status = _status_from_changes(contexts)
    if changed_status:
        return changed_status

    return _first_text(contexts, ("status", "state", "workflowState", "workflow_state"))


def _status_from_changes(contexts: Sequence[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        changes = context.get("changes")
        if isinstance(changes, Mapping):
            for field, change in changes.items():
                if _is_status_field(field):
                    status = _change_value(change)
                    if status:
                        return status

        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            status = _change_value(context.get(key))
            if status:
                return status

    return None


def _change_value(value: Any) -> str | None:
    if isinstance(value, str):
        return None

    if isinstance(value, Mapping):
        for key in ("to", "new", "newValue", "new_value", "after", "value"):
            text = _coerce_text(value.get(key))
            if text:
                return text

        if any(_is_status_field(value.get(key)) for key in ("field", "fieldName", "name", "key")):
            for key in ("to", "new", "newValue", "new_value", "after", "value"):
                text = _coerce_text(value.get(key))
                if text:
                    return text

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for item in value:
            status = _change_value(item)
            if status:
                return status

    return None


def _first_text(contexts: Sequence[Mapping[str, Any]], keys: Sequence[str]) -> str | None:
    for context in contexts:
        for key in keys:
            text = _coerce_text(context.get(key))
            if text:
                return text
    return None


def _coerce_text(value: Any) -> str | None:
    if isinstance(value, str):
        text = value.strip()
        return text or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "status", "identifier", "key", "id"):
            text = _coerce_text(value.get(key))
            if text:
                return text

    return None


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""

    text = str(value)
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def main() -> int:
    payload = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(payload), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
