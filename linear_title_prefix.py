"""Build Linear issue title updates for research-status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_TRIGGER_KEYS = ("trigger", "triggerType", "webhookType", "action", "type")
_DIRECT_STATUS_CHANGE_TRIGGERS = {
    "status changed",
    "status change",
    "state changed",
    "workflow state changed",
}
_GENERIC_UPDATE_TRIGGERS = {
    "issue updated",
    "updated issue",
    "update",
}
_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflow state",
    "workflowstate",
    "workflow status",
    "workflowstatus",
}
_NEW_STATUS_KEYS = (
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
)
_FALLBACK_STATUS_KEYS = ("status", "state", "workflowState", "workflow_state")
_ISSUE_ID_KEYS = ("id", "issueId", "issue_id", "identifier", "key")
_TITLE_KEYS = ("title", "name")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue-title update action when an issue moves to research.

    The function is intentionally side-effect free: callers can pass a Linear
    webhook or automation payload and apply the returned action through their
    own Linear client.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _candidate_contexts(event)
    if not _is_status_change(contexts):
        return None

    new_status = _extract_new_status(contexts)
    if _normalize_words(new_status) != TARGET_STATUS:
        return None

    issue_id = _extract_text(contexts, _ISSUE_ID_KEYS)
    title = _extract_text(contexts, _TITLE_KEYS)
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _candidate_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)

    add(event)
    add(event.get("triggerContext"))
    add(event.get("data"))
    add(event.get("issue"))

    data = event.get("data")
    if isinstance(data, Mapping):
        add(data.get("issue"))
        add(data.get("triggerContext"))

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        add(trigger_context.get("issue"))
        add(trigger_context.get("data"))

    return contexts


def _is_status_change(contexts: list[Mapping[str, Any]]) -> bool:
    trigger_values = {
        _normalize_words(context[key])
        for context in contexts
        for key in _TRIGGER_KEYS
        if key in context
    }

    if trigger_values & _DIRECT_STATUS_CHANGE_TRIGGERS:
        return True

    if trigger_values & _GENERIC_UPDATE_TRIGGERS:
        return _updated_fields_include_status(contexts)

    return False


def _updated_fields_include_status(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            if _field_collection_includes_status(context.get(key)):
                return True

        changes = context.get("changes")
        if isinstance(changes, Mapping) and any(
            _is_status_field(field_name) for field_name in changes
        ):
            return True
        if _field_collection_includes_status(changes):
            return True

    return False


def _field_collection_includes_status(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)
    if isinstance(value, Mapping):
        return any(_is_status_field(key) for key in value)
    if isinstance(value, list | tuple | set):
        return any(_field_collection_includes_status(item) for item in value)
    return False


def _is_status_field(value: Any) -> bool:
    return _normalize_words(_text_from_value(value)) in _STATUS_FIELD_NAMES


def _extract_new_status(contexts: list[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        for key in _NEW_STATUS_KEYS:
            if key in context:
                text = _text_from_value(context[key])
                if text:
                    return text

    for context in contexts:
        status = _status_from_changes(context.get("changes"))
        if status:
            return status

    for context in contexts:
        for key in _FALLBACK_STATUS_KEYS:
            if key in context:
                text = _text_from_value(context[key])
                if text:
                    return text

    return None


def _status_from_changes(value: Any) -> str | None:
    if not isinstance(value, Mapping):
        return None

    for key, change in value.items():
        if not _is_status_field(key):
            continue

        if isinstance(change, Mapping):
            for status_key in ("to", "after", "new", "newValue", "new_value", "value", "name"):
                if status_key in change:
                    text = _text_from_value(change[status_key])
                    if text:
                        return text
        else:
            text = _text_from_value(change)
            if text:
                return text

    return None


def _extract_text(contexts: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for context in contexts:
        for key in keys:
            if key in context:
                text = _text_from_value(context[key])
                if text:
                    return text
    return None


def _text_from_value(value: Any) -> str | None:
    if isinstance(value, str):
        text = value.strip()
        return text or None
    if isinstance(value, Mapping):
        for key in ("name", "title", "value", "id", "identifier", "key"):
            if key in value:
                text = _text_from_value(value[key])
                if text:
                    return text
    return None


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def _normalize_words(value: Any) -> str:
    text = _text_from_value(value)
    if not text:
        return ""
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def main() -> int:
    action = build_issue_title_update(json.load(sys.stdin))
    json.dump(action, sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
