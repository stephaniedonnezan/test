"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_DIRECT_STATUS_CHANGE_EVENTS = {
    "status change",
    "status changed",
    "state change",
    "state changed",
    "workflow state change",
    "workflow state changed",
}
_GENERIC_UPDATE_EVENTS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}
_TRIGGER_KEYS = (
    "trigger",
    "webhookType",
    "webhook_type",
    "action",
    "type",
    "event",
    "eventType",
    "event_type",
)
_NEW_STATUS_KEYS = (
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
)
_TITLE_KEYS = ("title", "issueTitle", "issue_title")
_ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "key", "id")
_CHANGE_KEYS = ("changes", "changed", "updatedFrom", "updated_from")
_UPDATED_FIELD_KEYS = (
    "updatedFields",
    "updated_fields",
    "changedFields",
    "changed_fields",
)


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update action when a Linear issue enters To Research.

    The Cursor automation payload is intentionally small, but Linear webhooks
    can nest issue data under ``data.issue``. This accepts both shapes and
    returns ``None`` for events that should not change the issue title.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = list(_candidate_contexts(event))
    if not _is_status_change_event(contexts):
        return None

    new_status = _extract_new_status(contexts)
    if _normalize_words(new_status) != TARGET_STATUS:
        return None

    title = _first_text(contexts, _TITLE_KEYS)
    issue_id = _first_text(contexts, _ISSUE_ID_KEYS)
    if not title or not issue_id:
        return None

    stripped_title = title.strip()
    if _has_research_prefix(stripped_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {stripped_title}",
    }


def _candidate_contexts(event: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    """Return likely metadata and issue-data containers in precedence order."""

    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and not any(value is item for item in contexts):
            contexts.append(value)

    trigger_context = event.get("triggerContext")
    add(trigger_context)
    add(event)

    for parent in tuple(contexts):
        data = parent.get("data")
        issue = parent.get("issue")
        add(data)
        add(issue)
        if isinstance(data, Mapping):
            add(data.get("issue"))
            add(data.get("node"))
        if isinstance(issue, Mapping):
            add(issue.get("state"))
            add(issue.get("workflowState"))
            add(issue.get("workflow_state"))

    return tuple(contexts)


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    direct_change = False
    generic_update = False

    for context in contexts:
        for key in _TRIGGER_KEYS:
            event_name = _normalize_words(context.get(key))
            if not event_name:
                continue
            if event_name in _DIRECT_STATUS_CHANGE_EVENTS:
                direct_change = True
            elif "status" in event_name.split() and "changed" in event_name.split():
                direct_change = True
            elif event_name in _GENERIC_UPDATE_EVENTS:
                generic_update = True

    return direct_change or (generic_update and _updated_fields_include_status(contexts))


def _updated_fields_include_status(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in _UPDATED_FIELD_KEYS:
            if _field_collection_mentions_status(context.get(key)):
                return True
        for key in _CHANGE_KEYS:
            if _changes_mention_status(context.get(key)):
                return True
    return False


def _field_collection_mentions_status(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(_is_status_field(key) for key in value)
    if isinstance(value, (list, tuple, set)):
        for item in value:
            if _field_collection_mentions_status(item):
                return True
            if _is_status_field(item):
                return True
    if isinstance(value, str):
        return _is_status_field(value)
    return False


def _changes_mention_status(value: Any) -> bool:
    if isinstance(value, Mapping):
        if any(_is_status_field(key) for key in value):
            return True
        return any(_changes_mention_status(item) for item in value.values())
    if isinstance(value, (list, tuple, set)):
        return any(_changes_mention_status(item) for item in value)
    return False


def _extract_new_status(contexts: list[Mapping[str, Any]]) -> Any:
    for context in contexts:
        for key in _NEW_STATUS_KEYS:
            status = _extract_name(context.get(key))
            if status:
                return status

    for context in contexts:
        for key in _CHANGE_KEYS:
            status = _extract_status_from_changes(context.get(key))
            if status:
                return status

    for context in contexts:
        for key in ("status", "state", "workflowState", "workflow_state"):
            status = _extract_name(context.get(key))
            if status:
                return status

    return None


def _extract_status_from_changes(value: Any) -> Any:
    if isinstance(value, Mapping):
        for key, changed_value in value.items():
            if _is_status_field(key):
                return _extract_changed_to_value(changed_value)
        for changed_value in value.values():
            status = _extract_status_from_changes(changed_value)
            if status:
                return status
    elif isinstance(value, (list, tuple)):
        for item in value:
            status = _extract_status_from_changes(item)
            if status:
                return status
    return None


def _extract_changed_to_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        for key in ("to", "toValue", "to_value", "newValue", "new_value", "after", "value"):
            status = _extract_name(value.get(key))
            if status:
                return status
        return _extract_name(value)
    return _extract_name(value)


def _extract_name(value: Any) -> Any:
    if isinstance(value, Mapping):
        for key in ("name", "label", "title"):
            if value.get(key):
                return value[key]
    return value


def _first_text(contexts: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def _is_status_field(value: Any) -> bool:
    normalized = _normalize_words(value).replace(" ", "")
    return normalized in {"status", "state", "workflowstate", "workflowstatus"}


def _normalize_words(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value.strip())
    words = re.sub(r"[^A-Za-z0-9]+", " ", spaced).lower().split()
    return " ".join(words)


def main() -> int:
    payload = json.load(sys.stdin)
    update = build_issue_title_update(payload)
    if update is not None:
        print(json.dumps(update))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
