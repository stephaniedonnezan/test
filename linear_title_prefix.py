"""Build Linear issue title updates for research-status automation.

The public entrypoint is ``build_issue_title_update``. It accepts the JSON-like
payload delivered by the automation trigger and returns a small action object
when the issue title should be prefixed.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


CURSOR_RESEARCH_PREFIX = "Cursor researching"
UPDATE_ACTION = "update_issue_title"

_EXPLICIT_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "statusName",
    "status_name",
    "stateName",
    "state_name",
    "workflowStateName",
    "workflow_state_name",
)
_STATUS_FIELD_KEYS = ("status", "state", "workflowState", "workflow_state")
_TITLE_KEYS = ("title", "name")
_ISSUE_ID_KEYS = ("id", "issueId", "issue_id", "identifier")
_TRIGGER_KEYS = (
    "trigger",
    "event",
    "eventType",
    "event_type",
    "webhookType",
    "webhook_type",
    "action",
    "type",
)
_STATUS_CHANGE_FIELDS = {
    "status",
    "statusid",
    "status_id",
    "state",
    "stateid",
    "state_id",
    "workflowstate",
    "workflowstateid",
    "workflow_state",
    "workflow_state_id",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when an issue moves to "to research".

    The handler is intentionally tolerant of both the flat Cursor automation
    trigger payload and nested Linear webhook payloads.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _event_contexts(event)
    if not _is_status_change_event(contexts):
        return None

    status = _extract_new_status(contexts)
    if _normalize_text(status) != "to research":
        return None

    issue_id = _first_text(contexts, _ISSUE_ID_KEYS)
    title = _first_text(contexts, _TITLE_KEYS)
    if not issue_id or not title:
        return None

    stripped_title = title.strip()
    if _has_research_prefix(stripped_title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id.strip(),
        "title": f"{CURSOR_RESEARCH_PREFIX}: {stripped_title}",
    }


def _event_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []
    seen: set[int] = set()

    def add_context(value: Any) -> None:
        if not isinstance(value, Mapping) or id(value) in seen:
            return
        seen.add(id(value))
        contexts.append(value)

    trigger_context = event.get("triggerContext")
    add_context(trigger_context)
    add_context(event)

    for value in list(contexts):
        for key in ("data", "issue", "node", "payload"):
            nested = value.get(key)
            add_context(nested)
            if isinstance(nested, Mapping):
                add_context(nested.get("issue"))

    return contexts


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    saw_issue_update = False

    for context in contexts:
        for key in _TRIGGER_KEYS:
            normalized = _normalize_text(context.get(key))
            if not normalized:
                continue
            if normalized in {
                "status changed",
                "status change",
                "state changed",
                "state change",
                "workflow state changed",
                "workflow state change",
            }:
                return True
            if normalized in {"update", "updated", "issue update", "issue updated", "updated issue"}:
                saw_issue_update = True

    return saw_issue_update and _has_status_field_change(contexts)


def _has_status_field_change(contexts: Iterable[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            if _contains_status_field(context.get(key)):
                return True

        updated_from = context.get("updatedFrom") or context.get("updated_from")
        if isinstance(updated_from, Mapping) and _contains_status_field(updated_from.keys()):
            return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _status_field_key(value) in _STATUS_CHANGE_FIELDS
    if isinstance(value, Mapping):
        return any(_contains_status_field(key) for key in value.keys())
    if isinstance(value, Iterable):
        return any(_contains_status_field(item) for item in value)
    return False


def _extract_new_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    context_list = list(contexts)

    explicit_status = _first_text(context_list, _EXPLICIT_STATUS_KEYS)
    if explicit_status:
        return explicit_status

    for context in context_list:
        for key in _STATUS_FIELD_KEYS:
            status = _status_text(context.get(key))
            if status:
                return status

    return None


def _status_text(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        return _first_text((value,), ("name", "title", "label"))
    return None


def _first_text(contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(CURSOR_RESEARCH_PREFIX.casefold())


def _normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    spaced = re.sub(r"[^A-Za-z0-9]+", " ", spaced)
    return " ".join(spaced.casefold().split())


def _status_field_key(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]+", "", value).casefold()


def _main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
