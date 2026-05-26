"""Build Linear issue title updates for Cursor research automation.

The automation trigger can arrive as a flat Cursor trigger context or as a
Linear-style webhook payload. This module keeps the decision pure: callers can
apply the returned update action using their Linear client.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_MARKER = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_CHANGE_FIELDS = {
    "status",
    "status id",
    "state",
    "state id",
    "workflow state",
    "workflow state id",
}
STATUS_CHANGE_SIGNALS = {
    "status changed",
    "state changed",
    "workflow state changed",
    "issue status changed",
    "issue state changed",
}
UPDATE_SIGNALS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to To Research.

    The returned action has the shape expected by the surrounding automation:
    ``{"action": "update_issue_title", "issueId": "...", "title": "..."}``.
    ``None`` means the event should not modify the issue title.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_change_event(contexts):
        return None

    new_status = _extract_new_status(contexts)
    if _normalize_words(new_status) != TARGET_STATUS:
        return None

    title = _extract_title(contexts)
    issue_id = _extract_issue_id(contexts)
    if not title or not issue_id:
        return None

    clean_title = title.strip()
    if _has_marker(clean_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_MARKER}: {clean_title}",
    }


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return likely payload scopes from most automation-specific to broadest."""

    contexts: list[Mapping[str, Any]] = []

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        contexts.append(trigger_context)

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            contexts.append(issue)
        contexts.append(data)

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        contexts.append(issue)

    contexts.append(event)
    return contexts


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    context_list = list(contexts)
    signal_keys = ("trigger", "webhookType", "eventType", "type", "action")

    for context in context_list:
        for key in signal_keys:
            if _normalize_words(context.get(key)) in STATUS_CHANGE_SIGNALS:
                return True

    for context in context_list:
        signal = _normalize_words(context.get("action"))
        trigger = _normalize_words(context.get("trigger"))
        event_type = _normalize_words(context.get("eventType"))
        payload_type = _normalize_words(context.get("type"))
        if {signal, trigger, event_type, payload_type} & UPDATE_SIGNALS:
            return _has_status_field_change(context_list)

    return False


def _has_status_field_change(contexts: Iterable[Mapping[str, Any]]) -> bool:
    for context in contexts:
        changed_fields = _iter_changed_field_names(context)
        if any(_normalize_words(field) in STATUS_CHANGE_FIELDS for field in changed_fields):
            return True
    return False


def _iter_changed_field_names(context: Mapping[str, Any]) -> Iterable[str]:
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        value = context.get(key)
        if isinstance(value, str):
            yield value
        elif isinstance(value, Iterable):
            for item in value:
                if isinstance(item, str):
                    yield item

    for key in ("updatedFrom", "updated_from", "changes"):
        value = context.get(key)
        if isinstance(value, Mapping):
            yield from (str(field) for field in value.keys())


def _extract_new_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    explicit_status_keys = (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "newWorkflowState",
        "new_workflow_state",
        "statusName",
        "status_name",
        "stateName",
        "state_name",
        "workflowStateName",
        "workflow_state_name",
    )
    context_list = list(contexts)

    for key in explicit_status_keys:
        status = _first_text_value(context_list, key)
        if status:
            return status

    for context in context_list:
        for key in ("status", "state", "workflowState", "workflow_state"):
            status = _status_text(context.get(key))
            if status:
                return status

    return None


def _extract_title(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    return _first_text_value(contexts, "title")


def _extract_issue_id(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    for key in ("issueId", "issue_id", "identifier", "id"):
        issue_id = _first_text_value(contexts, key)
        if issue_id:
            return issue_id
    return None


def _first_text_value(contexts: Iterable[Mapping[str, Any]], key: str) -> str | None:
    for context in contexts:
        value = context.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _status_text(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            nested = value.get(key)
            if isinstance(nested, str) and nested.strip():
                return nested
    return None


def _has_marker(title: str) -> bool:
    return title.lower().startswith(TITLE_MARKER.lower())


def _normalize_words(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value.strip())
    words = re.sub(r"[^A-Za-z0-9]+", " ", spaced)
    return re.sub(r"\s+", " ", words).strip().lower()


def main() -> int:
    payload = json.load(sys.stdin)
    result = build_issue_title_update(payload)
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
