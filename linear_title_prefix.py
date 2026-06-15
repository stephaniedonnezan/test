"""Build title update actions for Linear issues entering research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

STATUS_FIELD_NAMES = {
    "status",
    "status id",
    "state",
    "state id",
    "workflowstate",
    "workflow state",
    "workflow state id",
}
STATUS_CHANGE_EVENTS = {"statuschanged", "statechanged", "workflowstatechanged"}
UPDATE_EVENTS = {"update", "updated", "issueupdate", "issueupdated", "updatedissue"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to research."""
    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_change_event(contexts):
        return None

    new_status = _new_status(contexts)
    if _normalize_words(new_status) != _normalize_words(TARGET_STATUS):
        return None

    issue_id = _first_text(contexts, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_text(contexts, ("title", "issueTitle", "issue_title"))
    if not issue_id or not title:
        return None

    stripped_title = title.strip()
    if stripped_title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {stripped_title}",
    }


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return payload fragments ordered from most issue-specific to broadest."""
    contexts: list[Mapping[str, Any]] = []

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        contexts.append(trigger_context)

    data = event.get("data")
    if isinstance(data, Mapping):
        data_issue = data.get("issue")
        if isinstance(data_issue, Mapping):
            contexts.append(data_issue)
        contexts.append(data)

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        contexts.append(issue)

    contexts.append(event)
    return contexts


def _is_status_change_event(contexts: Sequence[Mapping[str, Any]]) -> bool:
    indicators = ("trigger", "webhookType", "action", "type", "event", "eventType")

    saw_update = False
    for context in contexts:
        for key in indicators:
            token = _normalize_token(context.get(key))
            if token in STATUS_CHANGE_EVENTS:
                return True
            if token in UPDATE_EVENTS:
                saw_update = True

    return saw_update and _updated_fields_include_status(contexts)


def _updated_fields_include_status(contexts: Sequence[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            fields = context.get(key)
            if isinstance(fields, str) and _is_status_field(fields):
                return True
            if isinstance(fields, Sequence) and not isinstance(fields, (str, bytes)):
                if any(_is_status_field(field) for field in fields):
                    return True

        for key in ("changes", "changed", "updatedFrom", "updated_from"):
            changes = context.get(key)
            if isinstance(changes, Mapping) and any(_is_status_field(field) for field in changes):
                return True

    return False


def _new_status(contexts: Sequence[Mapping[str, Any]]) -> str | None:
    explicit_keys = (
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
        "stateName",
        "workflowStateName",
    )
    status_keys = ("status", "state", "workflowState", "workflow_state")

    status = _first_text(contexts, explicit_keys)
    if status:
        return status

    for context in contexts:
        for key in ("changes", "changed"):
            changes = context.get(key)
            status = _status_from_changes(changes)
            if status:
                return status

    return _first_text(contexts, status_keys)


def _status_from_changes(changes: Any) -> str | None:
    if not isinstance(changes, Mapping):
        return None

    for field, value in changes.items():
        if _is_status_field(field):
            status = _to_text(value)
            if status:
                return status

    return None


def _first_text(contexts: Sequence[Mapping[str, Any]], keys: Sequence[str]) -> str | None:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            text = _to_text(value)
            if text:
                return text
    return None


def _to_text(value: Any) -> str | None:
    if isinstance(value, str):
        text = value.strip()
        return text or None
    if isinstance(value, Mapping):
        for key in ("to", "newValue", "new_value", "after", "current", "name", "title"):
            text = _to_text(value.get(key))
            if text:
                return text
    return None


def _is_status_field(value: Any) -> bool:
    return _normalize_words(value) in STATUS_FIELD_NAMES


def _normalize_words(value: Any) -> str:
    text = _coerce_text(value)
    if not text:
        return ""
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def _normalize_token(value: Any) -> str:
    return _normalize_words(value).replace(" ", "")


def _coerce_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        for key in ("name", "title", "id"):
            text = _coerce_text(value.get(key))
            if text:
                return text
    return ""


def main() -> None:
    """Read a JSON event from stdin and print the resulting action."""
    event = json.load(sys.stdin)
    result = build_issue_title_update(event)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
