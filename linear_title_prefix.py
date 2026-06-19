"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow state"}
_DIRECT_STATUS_CHANGE_EVENTS = {
    "status changed",
    "status change",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
}
_GENERIC_UPDATE_EVENTS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to To Research.

    The handler accepts both flat Cursor automation trigger contexts and nested
    Linear webhook payloads. It intentionally returns ``None`` when the payload
    is not a status-change event, is not moving to To Research, or the title is
    already prefixed.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _payload_contexts(event)
    if not _is_status_change_event(contexts):
        return None

    new_status = _new_status(contexts)
    if _normalize_phrase(new_status) != TARGET_STATUS:
        return None

    title = _first_text(contexts, ("title", "name", "issueTitle", "issue_title"))
    issue_id = _issue_id(contexts, event)
    if not title or not issue_id:
        return None

    clean_title = title.strip()
    if _has_research_prefix(clean_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {clean_title}",
    }


def _payload_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return payload mappings ordered from most issue-specific to broadest."""

    contexts: list[Mapping[str, Any]] = []

    trigger_context = _mapping_value(event.get("triggerContext"))
    if trigger_context:
        contexts.append(trigger_context)

    issue = _mapping_value(event.get("issue"))
    if issue:
        contexts.append(issue)

    data = _mapping_value(event.get("data"))
    if data:
        data_issue = _mapping_value(data.get("issue"))
        if data_issue:
            contexts.append(data_issue)
        contexts.append(data)

    contexts.append(event)
    return contexts


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    event_names = [
        normalized
        for context in contexts
        for normalized in (
            _normalize_phrase(context.get(key))
            for key in ("trigger", "action", "type", "webhookType", "eventType")
        )
        if normalized
    ]

    if any(name in _DIRECT_STATUS_CHANGE_EVENTS for name in event_names):
        return True

    if any(name in _GENERIC_UPDATE_EVENTS for name in event_names):
        return _status_was_updated(contexts)

    return False


def _status_was_updated(contexts: Iterable[Mapping[str, Any]]) -> bool:
    for context in contexts:
        updated_fields = context.get("updatedFields")
        if _fields_include_status(updated_fields):
            return True

        changes = _mapping_value(context.get("changes"))
        if changes and any(_is_status_field(key) for key in changes):
            return True

        updated_from = _mapping_value(context.get("updatedFrom"))
        if updated_from and any(_is_status_field(key) for key in updated_from):
            return True

    return False


def _new_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    explicit_keys = (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "newWorkflowState",
        "new_workflow_state",
        "statusName",
        "stateName",
        "workflowStateName",
    )
    status_keys = ("status", "state", "workflowState", "workflow_state")

    context_list = list(contexts)
    for context in context_list:
        value = _first_text([context], explicit_keys)
        if value:
            return value

    for context in context_list:
        changes = _mapping_value(context.get("changes"))
        if not changes:
            continue

        for key, value in changes.items():
            if not _is_status_field(key):
                continue
            text = _changed_to_text(value)
            if text:
                return text

    for context in context_list:
        value = _first_text([context], status_keys)
        if value:
            return value

    return None


def _changed_to_text(value: Any) -> str | None:
    if isinstance(value, Mapping):
        return _first_text([value], ("to", "toValue", "newValue", "after", "name"))

    return _text_value(value)


def _issue_id(contexts: Iterable[Mapping[str, Any]], event: Mapping[str, Any]) -> str | None:
    context_list = list(contexts)
    preferred = _first_text(
        context_list,
        ("issueId", "issue_id", "identifier", "key"),
    )
    if preferred:
        return preferred

    for context in context_list:
        if context is event and "automationId" in event and "triggerContext" in event:
            continue
        value = _text_value(context.get("id"))
        if value:
            return value

    return None


def _first_text(contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for context in contexts:
        for key in keys:
            if key not in context:
                continue
            value = _text_value(context[key])
            if value:
                return value
    return None


def _text_value(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None

    if isinstance(value, Mapping):
        return _first_text([value], ("name", "title", "label", "value"))

    return None


def _mapping_value(value: Any) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None


def _fields_include_status(fields: Any) -> bool:
    if isinstance(fields, str):
        return _is_status_field(fields)

    if isinstance(fields, Mapping):
        return any(_is_status_field(key) for key in fields)

    if isinstance(fields, Iterable):
        return any(_is_status_field(field) for field in fields)

    return False


def _is_status_field(value: Any) -> bool:
    normalized = _normalize_phrase(value).replace(" ", "")
    return normalized in {field.replace(" ", "") for field in _STATUS_FIELD_NAMES}


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def _normalize_phrase(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    with_camel_boundaries = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    words_only = re.sub(r"[^A-Za-z0-9]+", " ", with_camel_boundaries)
    return " ".join(words_only.casefold().split())


def main() -> int:
    payload = json.load(sys.stdin)
    result = build_issue_title_update(payload)
    if result is not None:
        print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
