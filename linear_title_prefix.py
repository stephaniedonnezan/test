"""Build Linear issue title updates for research status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflow state",
    "workflowstate",
    "workflow status",
}

_DIRECT_STATUS_CHANGE_MARKERS = {
    "status changed",
    "status change",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
    "status updated",
}

_GENERIC_UPDATE_MARKERS = {
    "update",
    "updated",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when an issue status changes to to research.

    The function is intentionally side-effect free so automation runners can pass
    its return value to their Linear update layer.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = list(_candidate_contexts(event))
    if not _is_status_change_event(contexts):
        return None

    if _normalize_status(_new_status(contexts)) != TARGET_STATUS:
        return None

    issue_id = _first_text(contexts, ("identifier", "key", "issueId", "issue_id", "id"))
    title = _first_text(contexts, ("title", "name", "summary"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if not title or title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _candidate_contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield useful payload scopes from flat and nested automation events."""

    seen: set[int] = set()
    queue: list[Any] = [event]

    while queue:
        value = queue.pop(0)
        if not isinstance(value, Mapping):
            continue

        value_id = id(value)
        if value_id in seen:
            continue
        seen.add(value_id)
        yield value

        for key in ("triggerContext", "data", "issue", "node", "payload"):
            nested = value.get(key)
            if isinstance(nested, Mapping):
                queue.append(nested)


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    markers = []
    for context in contexts:
        for key in ("trigger", "event", "action", "type", "webhookType"):
            marker = _normalize_words(context.get(key))
            if marker:
                markers.append(marker)

    if any(marker in _DIRECT_STATUS_CHANGE_MARKERS for marker in markers):
        return True

    if any(marker in _GENERIC_UPDATE_MARKERS for marker in markers):
        return _mentions_changed_status_field(contexts)

    return _mentions_changed_status_field(contexts) and _new_status(contexts) is not None


def _mentions_changed_status_field(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "changedFields", "fields", "updated_fields"):
            if _contains_status_field(context.get(key)):
                return True

        changes = context.get("changes")
        if isinstance(changes, Mapping):
            for field in changes:
                if _is_status_field(field):
                    return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)
    if isinstance(value, Mapping):
        return any(_is_status_field(key) or _contains_status_field(item) for key, item in value.items())
    if isinstance(value, Iterable):
        return any(_contains_status_field(item) for item in value)
    return False


def _is_status_field(value: Any) -> bool:
    return _normalize_words(value) in _STATUS_FIELD_NAMES


def _new_status(contexts: list[Mapping[str, Any]]) -> Any:
    explicit_keys = (
        "newStatus",
        "new_status",
        "toStatus",
        "targetStatus",
        "newState",
        "new_state",
        "statusName",
        "status_name",
    )
    for context in contexts:
        for key in explicit_keys:
            if key in context:
                return context[key]

    for context in contexts:
        changes = context.get("changes")
        if isinstance(changes, Mapping):
            changed_status = _status_from_changes(changes)
            if changed_status is not None:
                return changed_status

    for context in contexts:
        for key in ("status", "state", "workflowState", "workflow_state"):
            if key in context:
                return context[key]

    return None


def _status_from_changes(changes: Mapping[str, Any]) -> Any:
    for field, change in changes.items():
        if not _is_status_field(field):
            continue
        if isinstance(change, Mapping):
            for key in ("to", "after", "new", "newValue", "value", "name"):
                if key in change:
                    return change[key]
        return change
    return None


def _first_text(contexts: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            text = _text_value(value)
            if text:
                return text
    return None


def _text_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, Mapping):
        for key in ("name", "title", "identifier", "key", "id"):
            text = _text_value(value.get(key))
            if text:
                return text
        return None
    text = str(value).strip()
    return text or None


def _normalize_status(value: Any) -> str:
    return _normalize_words(_text_value(value))


def _normalize_words(value: Any) -> str:
    text = _text_value(value)
    if not text:
        return ""
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[_\-/]+", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.casefold().split())


def main() -> int:
    """Read a JSON event from stdin and print the requested title update."""

    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    print(json.dumps(update, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
