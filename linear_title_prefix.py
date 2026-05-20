"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections import deque
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_CONTEXT_KEYS = ("triggerContext", "payload", "data", "issue", "node")
_ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "id")
_TITLE_KEYS = ("title",)
_TRIGGER_KEYS = ("trigger", "event", "action", "type", "webhookType", "webhook_type")
_STATUS_CHANGE_MARKERS = {
    "status changed",
    "status change",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
    "status updated",
    "state updated",
    "workflow state updated",
}
_UPDATE_MARKERS = {"update", "updated", "issue update", "issue updated", "updated issue"}
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
_EXPLICIT_STATUS_KEYS = (
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
    "newWorkflowStateName",
    "new_workflow_state_name",
    "statusName",
    "status_name",
    "stateName",
    "state_name",
    "workflowStateName",
    "workflow_state_name",
)
_STATUS_KEYS = ("status", "state", "workflowState", "workflow_state")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves into To Research."""

    if not isinstance(event, Mapping):
        return None

    contexts = list(_iter_contexts(event))
    if not _is_status_change_event(contexts):
        return None

    status = _new_status(contexts)
    if _normalize_words(status) != TARGET_STATUS:
        return None

    issue_id, title = _issue_identity(event, contexts)
    if not issue_id or not title:
        return None

    clean_title = title.strip()
    if not clean_title or _has_research_prefix(clean_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {clean_title}",
    }


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    context_list = list(contexts)
    if _has_status_change_trigger(context_list):
        return True

    if _has_update_trigger(context_list) and _has_changed_status_field(context_list):
        return True

    return not _has_any_trigger(context_list) and _has_changed_status_field(context_list)


def _has_status_change_trigger(contexts: Iterable[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in _TRIGGER_KEYS:
            marker = _normalize_words(context.get(key))
            if marker in _STATUS_CHANGE_MARKERS:
                return True
    return False


def _has_update_trigger(contexts: Iterable[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in _TRIGGER_KEYS:
            marker = _normalize_words(context.get(key))
            if marker in _UPDATE_MARKERS:
                return True
    return False


def _has_any_trigger(contexts: Iterable[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in _TRIGGER_KEYS:
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return True
    return False


def _has_changed_status_field(contexts: Iterable[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in _UPDATED_FIELD_KEYS:
            if _contains_status_field(context.get(key)):
                return True

        for key in _UPDATED_FROM_KEYS:
            value = context.get(key)
            if isinstance(value, Mapping) and any(_is_status_field_name(field) for field in value):
                return True
    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field_name(value)
    if isinstance(value, Mapping):
        return any(_is_status_field_name(field) for field in value) or any(
            _contains_status_field(item) for item in value.values()
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
            elif isinstance(value, str) and value.strip():
                return value

    return None


def _issue_identity(
    event: Mapping[str, Any], contexts: Iterable[Mapping[str, Any]]
) -> tuple[str | None, str | None]:
    context_list = list(contexts)
    for context in _candidate_issue_contexts(event, context_list):
        title = _first_text([context], _TITLE_KEYS)
        if not title:
            continue

        issue_id = _first_text([context], _ISSUE_ID_KEYS)
        if issue_id:
            return issue_id, title

        fallback_id = _first_text(context_list, ("issueId", "issue_id", "identifier"))
        return fallback_id, title

    return None, None


def _candidate_issue_contexts(
    event: Mapping[str, Any], contexts: Iterable[Mapping[str, Any]]
) -> Iterable[Mapping[str, Any]]:
    preferred_paths = (
        ("triggerContext",),
        ("data", "issue"),
        ("payload", "issue"),
        ("issue",),
        ("data",),
        ("payload", "data"),
        ("node",),
        (),
    )

    seen: set[int] = set()
    for path in preferred_paths:
        context = _mapping_at_path(event, path)
        if context is not None and id(context) not in seen:
            seen.add(id(context))
            yield context

    for context in contexts:
        if id(context) not in seen and _first_text([context], _TITLE_KEYS):
            seen.add(id(context))
            yield context


def _mapping_at_path(event: Mapping[str, Any], path: tuple[str, ...]) -> Mapping[str, Any] | None:
    current: Any = event
    for key in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current if isinstance(current, Mapping) else None


def _iter_contexts(root: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely event and issue dictionaries before falling back to nested mappings."""

    queue: deque[Any] = deque([root])
    seen: set[int] = set()

    while queue:
        current = queue.popleft()
        if not isinstance(current, Mapping):
            continue

        current_id = id(current)
        if current_id in seen:
            continue

        seen.add(current_id)
        yield current

        for key in _CONTEXT_KEYS:
            child = current.get(key)
            if isinstance(child, Mapping):
                queue.append(child)

    for mapping in _iter_all_mappings(root):
        if id(mapping) not in seen:
            seen.add(id(mapping))
            yield mapping


def _iter_all_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    queue: deque[Any] = deque([value])
    seen: set[int] = set()

    while queue:
        current = queue.popleft()
        if isinstance(current, Mapping):
            current_id = id(current)
            if current_id in seen:
                continue
            seen.add(current_id)
            yield current
            queue.extend(current.values())
        elif isinstance(current, list):
            queue.extend(current)


def _first_text(contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    context_list = list(contexts)
    for key in keys:
        for context in context_list:
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value
            if value is not None and not isinstance(value, (Mapping, list, tuple, set, bool)):
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


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(TITLE_PREFIX.casefold())


def main() -> int:
    """Read an event JSON document from stdin and print the update action."""

    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
