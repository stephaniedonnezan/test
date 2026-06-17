"""Build Linear issue title updates for Cursor research status changes.

The automation receives webhook payloads from a few sources.  The public
entrypoint below keeps the behavior small and deterministic: when an issue is
moving to "To Research", return the title update action; otherwise no-op.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
PREFIXED_TITLE = f"{PREFIX}: "
RESEARCH_STATUS = "toresearch"

DIRECT_STATUS_CHANGE_TRIGGERS = {
    "statuschanged",
    "statuschange",
    "statechanged",
    "statechange",
    "workflowstatechanged",
    "workflowstatechange",
}

GENERIC_ISSUE_UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issueupdated",
    "updatedissue",
    "issueupdate",
}

STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflowstate",
    "workflowstatus",
}

EXPLICIT_STATUS_KEYS = (
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
    "stateName",
    "state_name",
    "workflowStateName",
    "workflow_state_name",
)

ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "key", "id")


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update action for Linear issues moved to To Research."""

    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    issue = _issue_context(contexts)

    if not _is_status_change_event(contexts):
        return None

    new_status = _new_status(contexts)
    if _normalize_token(new_status) != RESEARCH_STATUS:
        return None

    issue_id = _issue_id(contexts, issue)
    title = _issue_title(contexts, issue)
    if not issue_id or not title:
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": title if _has_prefix(title) else f"{PREFIXED_TITLE}{title}",
    }


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = [event]

    for key in ("triggerContext", "data", "issue"):
        value = event.get(key)
        if isinstance(value, Mapping):
            contexts.append(value)

    data = event.get("data")
    if isinstance(data, Mapping):
        for key in ("issue", "node"):
            value = data.get(key)
            if isinstance(value, Mapping):
                contexts.append(value)

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        for key in ("issue", "data"):
            value = trigger_context.get(key)
            if isinstance(value, Mapping):
                contexts.append(value)

    return contexts


def _issue_context(contexts: list[Mapping[str, Any]]) -> Mapping[str, Any]:
    for context in contexts:
        for key in ("issue", "node"):
            value = context.get(key)
            if isinstance(value, Mapping):
                return value

    # Flat automation trigger contexts carry issue id and title directly.
    return contexts[-1] if contexts else {}


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    trigger_values = []
    for context in contexts:
        for key in ("trigger", "webhookType", "action", "type", "eventType"):
            value = context.get(key)
            if isinstance(value, str):
                trigger_values.append(_normalize_token(value))

    if any(value in DIRECT_STATUS_CHANGE_TRIGGERS for value in trigger_values):
        return True

    if any(value in GENERIC_ISSUE_UPDATE_TRIGGERS for value in trigger_values):
        return _has_status_field_change(contexts)

    return False


def _has_status_field_change(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "changedFields"):
            fields = context.get(key)
            if _contains_status_field(fields):
                return True

        for key in ("changes", "changed", "updatedFrom", "previous"):
            changes = context.get(key)
            if isinstance(changes, Mapping):
                if any(_normalize_token(field) in STATUS_FIELD_NAMES for field in changes):
                    return True
            elif _contains_status_field(changes):
                return True

    return False


def _contains_status_field(fields: Any) -> bool:
    if isinstance(fields, str):
        return _normalize_token(fields) in STATUS_FIELD_NAMES

    if isinstance(fields, Mapping):
        return any(_normalize_token(field) in STATUS_FIELD_NAMES for field in fields)

    if isinstance(fields, (list, tuple, set)):
        return any(_contains_status_field(field) for field in fields)

    return False


def _new_status(contexts: list[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        for key in EXPLICIT_STATUS_KEYS:
            value = _value_name(context.get(key))
            if value:
                return value

    for context in contexts:
        changes = context.get("changes")
        if isinstance(changes, Mapping):
            value = _status_from_changes(changes)
            if value:
                return value

    for context in contexts:
        for key in ("status", "state", "workflowState"):
            value = _value_name(context.get(key))
            if value:
                return value

    return None


def _status_from_changes(changes: Mapping[str, Any]) -> str | None:
    for key in ("status", "state", "workflowState"):
        value = changes.get(key)
        if isinstance(value, Mapping):
            for next_key in ("to", "new", "newValue", "after", "name"):
                next_value = _value_name(value.get(next_key))
                if next_value:
                    return next_value
        else:
            named_value = _value_name(value)
            if named_value:
                return named_value

    return None


def _issue_id(
    contexts: list[Mapping[str, Any]], issue: Mapping[str, Any]
) -> str | None:
    for context in [issue, *contexts]:
        for key in ISSUE_ID_KEYS:
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

    return None


def _issue_title(
    contexts: list[Mapping[str, Any]], issue: Mapping[str, Any]
) -> str | None:
    for context in [issue, *contexts]:
        value = context.get("title")
        if isinstance(value, str) and value.strip():
            return value.strip()

    return None


def _value_name(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()

    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            nested = value.get(key)
            if isinstance(nested, str) and nested.strip():
                return nested.strip()

    return None


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def _normalize_token(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    return re.sub(r"[^a-z0-9]", "", value.lower())


def main() -> int:
    payload = json.load(sys.stdin)
    result = build_issue_title_update(payload)
    if result is not None:
        print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
