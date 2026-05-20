"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_CONTEXT_KEYS = ("triggerContext", "payload", "data", "issue", "node")
_ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "id")
_TITLE_KEYS = ("title",)
_EXPLICIT_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "newWorkflowState",
    "new_workflow_state",
    "newWorkflowStateName",
    "new_workflow_state_name",
)
_STATUS_KEYS = ("status", "state", "workflowState", "workflow_state")
_TRIGGER_KEYS = ("trigger", "event", "action", "type", "webhookType", "webhook_type")
_UPDATED_FIELD_KEYS = ("updatedFields", "updated_fields", "changedFields", "changed_fields")
_UPDATED_FROM_KEYS = ("updatedFrom", "updated_from", "previousValues", "previous_values")
_STATUS_FIELD_NAMES = {
    "status",
    "statusid",
    "statusname",
    "state",
    "stateid",
    "statename",
    "workflowstate",
    "workflowstateid",
    "workflowstatename",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title-update action when a Linear issue moves to research."""

    if not isinstance(event, Mapping):
        return None

    contexts = list(_iter_contexts(event))
    if not _is_status_change_event(contexts):
        return None

    new_status = _new_status(contexts)
    if _normalize_words(new_status) != TARGET_STATUS:
        return None

    issue_id = _issue_id(contexts)
    title = _first_text(contexts, _TITLE_KEYS)
    if not issue_id or not title:
        return None

    clean_title = title.strip()
    if not clean_title or _has_prefix(clean_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {clean_title}",
    }


def _iter_contexts(root: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely event/issue dictionaries without descending into status objects."""

    seen: set[int] = set()
    stack: list[Mapping[str, Any]] = [root]

    while stack:
        current = stack.pop(0)
        current_id = id(current)
        if current_id in seen:
            continue
        seen.add(current_id)
        yield current

        for key in _CONTEXT_KEYS:
            child = current.get(key)
            if isinstance(child, Mapping):
                stack.append(child)


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    context_list = list(contexts)
    if _has_status_change_trigger(context_list):
        return True

    if not _has_update_trigger(context_list):
        return False

    return _has_changed_status_field(context_list)


def _has_status_change_trigger(contexts: Iterable[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in _TRIGGER_KEYS:
            normalized = _normalize_words(context.get(key))
            if normalized in {
                "status changed",
                "status change",
                "state changed",
                "state change",
                "workflow state changed",
                "workflow state change",
            }:
                return True
            if any(
                phrase in normalized
                for phrase in (
                    "status changed",
                    "status change",
                    "state changed",
                    "state change",
                    "workflow state changed",
                    "workflow state change",
                )
            ):
                return True
    return False


def _has_update_trigger(contexts: Iterable[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in _TRIGGER_KEYS:
            normalized = _normalize_words(context.get(key))
            if normalized in {"update", "updated", "issue update", "issue updated", "updated issue"}:
                return True
    return False


def _has_changed_status_field(contexts: Iterable[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in _UPDATED_FIELD_KEYS:
            if _contains_status_field(context.get(key)):
                return True
        for key in _UPDATED_FROM_KEYS:
            changed = context.get(key)
            if isinstance(changed, Mapping) and any(_is_status_field_name(field) for field in changed):
                return True
    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field_name(value)
    if isinstance(value, Mapping):
        return any(_contains_status_field(item) for item in value.values()) or any(
            _is_status_field_name(field) for field in value
        )
    if isinstance(value, Iterable):
        return any(_contains_status_field(item) for item in value)
    return False


def _is_status_field_name(value: Any) -> bool:
    return _normalize_key(value) in _STATUS_FIELD_NAMES


def _new_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    context_list = list(contexts)
    explicit = _first_text(context_list, _EXPLICIT_STATUS_KEYS)
    if explicit:
        return explicit

    for context in context_list:
        for key in _STATUS_KEYS:
            value = context.get(key)
            if isinstance(value, Mapping):
                name = _first_text([value], ("name", "title"))
                if name:
                    return name
            elif isinstance(value, str):
                return value

    return None


def _issue_id(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    context_list = list(contexts)
    explicit = _first_text(context_list, _ISSUE_ID_KEYS[:-1])
    if explicit:
        return explicit

    issue_like_contexts = [context for context in context_list if _first_text([context], _TITLE_KEYS)]
    issue_id = _first_text(issue_like_contexts, ("id",))
    if issue_id:
        return issue_id

    return _first_text(context_list, ("id",))


def _first_text(contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for key in keys:
        for context in contexts:
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value
            if value is not None and not isinstance(value, (Mapping, list, tuple, set)):
                text = str(value).strip()
                if text:
                    return text
    return None


def _normalize_words(value: Any) -> str:
    if value is None:
        return ""

    text = str(value)
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.casefold().split())


def _normalize_key(value: Any) -> str:
    return _normalize_words(value).replace(" ", "")


def _has_prefix(title: str) -> bool:
    return title.casefold().startswith(TITLE_PREFIX.casefold())


def main() -> int:
    """Read an event JSON document from stdin and print the update action."""

    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    update = build_issue_title_update(event)
    if update:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
