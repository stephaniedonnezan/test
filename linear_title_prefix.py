"""Build Linear issue title updates for research-status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_DIRECT_STATUS_TRIGGERS = {
    "status changed",
    "status change",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
    "issue status changed",
    "issue state changed",
}

_UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}

_STATUS_FIELD_NAMES = {
    "status",
    "status id",
    "state",
    "state id",
    "workflow state",
    "workflow state id",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title-update action when a Linear issue moves to To Research.

    The function is intentionally side-effect free. Callers can execute the
    returned action with their Linear client, or ignore ``None`` when the event
    is not a matching status transition.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    new_status = _extract_new_status(event)
    if _normalize_words(new_status) != TARGET_STATUS:
        return None

    title = _extract_issue_title(event)
    issue_id = _extract_issue_id(event)
    if title is None or issue_id is None:
        return None

    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    trigger_names = {
        _normalize_words(value)
        for context in _event_metadata_contexts(event)
        for key in ("trigger", "webhookType", "webhook_type", "action", "type", "eventType")
        if (value := context.get(key)) is not None
    }

    if trigger_names & _DIRECT_STATUS_TRIGGERS:
        return True

    if trigger_names & _UPDATE_TRIGGERS:
        return _changed_fields_include_status(event)

    return False


def _changed_fields_include_status(event: Mapping[str, Any]) -> bool:
    for context in _all_mapping_contexts(event):
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            if key in context and _value_mentions_status_field(context[key]):
                return True

        for key in ("changes", "changed", "updatedFrom", "updated_from", "previousValues"):
            value = context.get(key)
            if isinstance(value, Mapping) and _mapping_mentions_status_field(value):
                return True

    return False


def _value_mentions_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_words(value) in _STATUS_FIELD_NAMES

    if isinstance(value, Mapping):
        return _mapping_mentions_status_field(value)

    if isinstance(value, Iterable):
        return any(_value_mentions_status_field(item) for item in value)

    return False


def _mapping_mentions_status_field(value: Mapping[str, Any]) -> bool:
    return any(_normalize_words(key) in _STATUS_FIELD_NAMES for key in value)


def _extract_new_status(event: Mapping[str, Any]) -> str | None:
    contexts = _issue_contexts(event)

    for key in (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "newWorkflowState",
        "new_workflow_state",
    ):
        for context in contexts:
            if key in context:
                return _string_value(context[key])

    for context in _all_mapping_contexts(event):
        changes = context.get("changes")
        if isinstance(changes, Mapping):
            for key in ("status", "state", "workflowState", "workflow_state"):
                status = _status_from_change_value(changes.get(key))
                if status is not None:
                    return status

    for key in ("status", "state", "workflowState", "workflow_state"):
        for context in contexts:
            if key in context:
                return _string_value(context[key])

    return None


def _status_from_change_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("to", "new", "after", "name"):
            if key in value:
                return _string_value(value[key])

    return _string_value(value)


def _extract_issue_title(event: Mapping[str, Any]) -> str | None:
    for context in _issue_contexts(event):
        for key in ("title", "issueTitle", "issue_title"):
            if key in context:
                return _string_value(context[key])
    return None


def _extract_issue_id(event: Mapping[str, Any]) -> str | None:
    for context in _issue_contexts(event):
        for key in ("issueId", "issue_id", "identifier", "key", "id"):
            if key in context:
                return _string_value(context[key])
    return None


def _issue_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return likely issue payloads before generic event metadata."""

    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)

    trigger_context = event.get("triggerContext") or event.get("trigger_context")
    data = event.get("data")
    issue = event.get("issue")

    add(trigger_context)
    if isinstance(data, Mapping):
        add(data.get("issue"))
        add(data.get("node"))
        add(data.get("object"))
    add(issue)
    add(data)
    add(event)

    return contexts


def _event_metadata_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = [event]
    for key in ("triggerContext", "trigger_context", "data"):
        value = event.get(key)
        if isinstance(value, Mapping):
            contexts.append(value)
    return contexts


def _all_mapping_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []
    stack = [event]
    seen: set[int] = set()

    while stack:
        value = stack.pop()
        if not isinstance(value, Mapping) or id(value) in seen:
            continue

        seen.add(id(value))
        contexts.append(value)
        for child in value.values():
            if isinstance(child, Mapping):
                stack.append(child)
            elif isinstance(child, list):
                stack.extend(item for item in child if isinstance(item, Mapping))

    return contexts


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())


def _string_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("name", "title", "label", "identifier", "key", "id"):
            if key in value:
                return _string_value(value[key])
        return None

    if value is None:
        return None

    string = str(value).strip()
    return string or None


def _normalize_words(value: Any) -> str:
    string = _string_value(value)
    if string is None:
        return ""

    string = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", string)
    string = re.sub(r"[^A-Za-z0-9]+", " ", string)
    return re.sub(r"\s+", " ", string).strip().casefold()


def main() -> int:
    payload = json.load(sys.stdin)
    update = build_issue_title_update(payload)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
