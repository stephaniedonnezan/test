"""Build title update actions for Linear issues entering research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_CONTEXT_KEYS = (
    "triggerContext",
    "trigger_context",
    "payload",
    "body",
    "data",
    "issue",
    "node",
)
_TRIGGER_KEYS = (
    "trigger",
    "action",
    "event",
    "eventType",
    "event_type",
    "type",
    "webhookType",
    "webhook_type",
)
_EXPLICIT_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "newWorkflowState",
    "new_workflow_state",
    "toStatus",
    "to_status",
    "targetStatus",
    "target_status",
    "statusName",
    "status_name",
    "stateName",
    "state_name",
    "workflowStateName",
    "workflow_state_name",
)
_FALLBACK_STATUS_KEYS = ("status", "state", "workflowState", "workflow_state")
_UPDATED_FIELD_KEYS = (
    "updatedFields",
    "updated_fields",
    "changedFields",
    "changed_fields",
    "updatedField",
    "updated_field",
)
_STATUS_FIELD_NAMES = {"status", "state", "workflow state", "workflowstate"}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear issue-title update action when the event enters research.

    The automation runtime supplies slightly different webhook shapes depending on
    trigger source, so this function accepts both the flat triggerContext payload
    and common nested Linear issue update payloads.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _collect_contexts(event)
    if not _is_status_change_event(contexts):
        return None

    status = _current_status(contexts)
    if _normalize(status) != TARGET_STATUS:
        return None

    issue_id = _first_text(contexts, ("issueId", "issue_id", "identifier"))
    if issue_id is None:
        issue_id = _issue_id_from_issue_context(contexts)

    title = _first_text(contexts, ("title", "name"))
    if issue_id is None or title is None:
        return None

    title = title.strip()
    if title.lower().startswith(TITLE_PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _collect_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []
    seen: set[int] = set()

    def visit(value: Any) -> None:
        if not isinstance(value, Mapping):
            return
        object_id = id(value)
        if object_id in seen:
            return
        seen.add(object_id)
        contexts.append(value)
        for key in _CONTEXT_KEYS:
            visit(value.get(key))

    visit(event)
    return contexts


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    context_list = list(contexts)
    has_update_event = False

    for context in context_list:
        for key in _TRIGGER_KEYS:
            normalized = _normalize(context.get(key))
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
                has_update_event = True

    return has_update_event and _updated_status_fields(context_list)


def _updated_status_fields(contexts: Iterable[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in _UPDATED_FIELD_KEYS:
            fields = context.get(key)
            if fields is None:
                continue
            if _contains_status_field(fields):
                return True

        updated_from = context.get("updatedFrom") or context.get("updated_from")
        if isinstance(updated_from, Mapping):
            if any(_normalize(field) in _STATUS_FIELD_NAMES for field in updated_from):
                return True

        changes = context.get("changes")
        if isinstance(changes, Mapping):
            if any(_normalize(field) in _STATUS_FIELD_NAMES for field in changes):
                return True
        elif _contains_status_field(changes):
            return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, Mapping):
        values = list(value.keys()) + list(value.values())
    elif isinstance(value, str):
        values = [value]
    elif isinstance(value, Iterable):
        values = list(value)
    else:
        values = []

    for field in values:
        if isinstance(field, Mapping):
            name = field.get("name") or field.get("field") or field.get("key")
        else:
            name = field
        if _normalize(name) in _STATUS_FIELD_NAMES:
            return True
    return False


def _current_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    context_list = list(contexts)

    for context in context_list:
        value = _first_status_text(context, _EXPLICIT_STATUS_KEYS)
        if value is not None:
            return value

    for context in context_list:
        value = _first_status_text(context, _FALLBACK_STATUS_KEYS)
        if value is not None:
            return value

    return None


def _first_status_text(context: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for key in keys:
        value = context.get(key)
        if isinstance(value, Mapping):
            value = value.get("name") or value.get("title")
        text = _coerce_text(value)
        if text is not None:
            return text
    return None


def _first_text(contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for context in contexts:
        for key in keys:
            text = _coerce_text(context.get(key))
            if text is not None:
                return text
    return None


def _issue_id_from_issue_context(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        if _coerce_text(context.get("title")) is None:
            continue
        text = _coerce_text(context.get("id"))
        if text is not None:
            return text
    return None


def _coerce_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize(value: Any) -> str:
    text = _coerce_text(value)
    if text is None:
        return ""

    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[_\-/]+", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def main() -> int:
    action = build_issue_title_update(json.load(sys.stdin))
    if action is not None:
        print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
