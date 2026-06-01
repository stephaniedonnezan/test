"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_CAMEL_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_WHITESPACE = re.compile(r"\s+")

_NEW_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "newWorkflowState",
    "new_workflow_state",
)
_STATUS_KEYS = ("status", "state", "workflowState", "workflow_state", "stateName", "statusName")
_ISSUE_ID_KEYS = ("issueId", "issue_id", "id", "identifier")
_TITLE_KEYS = ("title", "name")
_TRIGGER_KEYS = ("trigger", "webhookType", "action", "type", "eventType")
_UPDATED_FIELD_KEYS = (
    "updatedFields",
    "updated_fields",
    "changedFields",
    "changed_fields",
    "updatedFrom",
    "updated_from",
    "changes",
)
_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "state id",
    "workflow state",
    "workflow state id",
    "workflowstate",
    "workflowstate id",
}
_DIRECT_STATUS_CHANGE_TRIGGERS = {
    "status changed",
    "status change",
    "status updated",
    "state changed",
    "state change",
    "state updated",
    "workflow state changed",
    "workflow state change",
    "workflow state updated",
}
_UPDATE_TRIGGERS = {"update", "updated", "issue update", "issue updated", "updated issue"}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to To Research.

    The automation trigger payload can be flat, as in Cursor Automation's
    `triggerContext`, or shaped like a nested Linear webhook payload.
    """
    if not isinstance(event, Mapping):
        return None

    contexts = _priority_contexts(event)
    if not _is_status_change_event(contexts):
        return None

    new_status = _first_status(contexts)
    if _normalize(new_status) != TARGET_STATUS:
        return None

    title = _first_text(contexts, _TITLE_KEYS)
    issue_id = _first_text(contexts, _ISSUE_ID_KEYS)
    if not title or not issue_id:
        return None

    title = title.strip()
    if not title or _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _priority_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []
    seen: set[int] = set()

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and id(value) not in seen:
            seen.add(id(value))
            contexts.append(value)

    trigger_context = event.get("triggerContext")
    data = event.get("data")
    issue = event.get("issue")

    add(trigger_context)
    if isinstance(data, Mapping):
        add(data.get("issue"))
        add(data.get("node"))
    add(issue)
    add(data)
    add(event)

    return contexts


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    normalized_triggers = {
        normalized
        for context in contexts
        for key in _TRIGGER_KEYS
        if (normalized := _normalize(context.get(key)))
    }

    if normalized_triggers & _DIRECT_STATUS_CHANGE_TRIGGERS:
        return True

    if normalized_triggers & _UPDATE_TRIGGERS:
        return _updated_fields_include_status(contexts)

    return False


def _updated_fields_include_status(contexts: Iterable[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in _UPDATED_FIELD_KEYS:
            if key in context and _contains_status_field(context[key]):
                return True
    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(_is_status_field(key) for key in value.keys())

    if isinstance(value, str):
        parts = re.split(r"[,;]", value)
        return any(_is_status_field(part) for part in parts)

    if isinstance(value, Iterable):
        return any(_contains_status_field(item) for item in value)

    return False


def _is_status_field(value: Any) -> bool:
    normalized = _normalize(value)
    return normalized in _STATUS_FIELD_NAMES


def _first_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    context_list = list(contexts)
    return _first_text(context_list, _NEW_STATUS_KEYS) or _first_text(context_list, _STATUS_KEYS)


def _first_text(contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for context in contexts:
        for key in keys:
            if key in context:
                text = _coerce_text(context[key])
                if text:
                    return text
    return None


def _coerce_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    if isinstance(value, Mapping):
        return _first_text([value], ("name", "title", "id", "identifier"))
    return str(value).strip() or None


def _normalize(value: Any) -> str:
    text = _coerce_text(value)
    if not text:
        return ""
    text = _CAMEL_BOUNDARY.sub(" ", text)
    text = re.sub(r"[_\-/]+", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return _WHITESPACE.sub(" ", text).strip().lower()


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def main() -> int:
    """Read a JSON event from stdin and print the computed action as JSON."""
    event = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(event)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
