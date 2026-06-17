"""Build Linear issue title updates for research status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_EVENT_KEYS = ("trigger", "webhookType", "eventType", "type", "action")
_EXPLICIT_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newStatusName",
    "new_status_name",
    "toStatus",
    "to_status",
    "toState",
    "to_state",
    "newState",
    "new_state",
    "workflowStateName",
    "workflow_state_name",
)
_CURRENT_STATUS_KEYS = ("status", "state", "workflowState", "workflow_state")
_CHANGED_STATUS_VALUE_KEYS = ("newValue", "new_value", "to", "after", "name", "value")
_ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "key", "id")
_ISSUE_TITLE_KEYS = ("title", "name")
_STATUS_CHANGE_KEYS = ("updatedFields", "changedFields", "changes", "updatedFrom")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue title update action when an event moves to research."""

    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_change_event(contexts):
        return None

    if _normalize(_first_status(contexts)) != TARGET_STATUS:
        return None

    issue_id = _first_text(contexts, _ISSUE_ID_KEYS)
    title = _first_text(contexts, _ISSUE_TITLE_KEYS)
    if not issue_id or not title:
        return None

    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return likely metadata and issue objects in precedence order."""

    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)

    add(event.get("triggerContext"))
    add(event)
    for container_key in ("payload", "data", "issue", "resource"):
        container = event.get(container_key)
        add(container)
        if isinstance(container, Mapping):
            for nested_key in ("triggerContext", "issue", "data", "resource"):
                add(container.get(nested_key))

    return contexts


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    contexts = list(contexts)
    if any(_is_direct_status_change(context.get(key)) for context in contexts for key in _EVENT_KEYS):
        return True

    if any(_has_status_change_metadata(context) for context in contexts):
        return True

    return False


def _is_direct_status_change(value: Any) -> bool:
    normalized = _normalize(value)
    if not normalized:
        return False

    mentions_status = "status" in normalized or "state" in normalized
    mentions_change = "changed" in normalized or "change" in normalized
    return mentions_status and mentions_change


def _has_status_change_metadata(context: Mapping[str, Any]) -> bool:
    for key in _STATUS_CHANGE_KEYS:
        value = context.get(key)
        if _contains_status_field(value):
            return True
    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, Mapping):
        if any(_looks_like_status_field(key) for key in value):
            return True

        return any(
            _looks_like_status_field(value.get(key))
            for key in ("field", "fieldName", "field_name", "name", "key")
        )

    if isinstance(value, str):
        return _looks_like_status_field(value)

    if isinstance(value, Iterable):
        return any(_contains_status_field(item) for item in value)

    return False


def _looks_like_status_field(value: Any) -> bool:
    normalized = _normalize(value)
    if not normalized:
        return False

    tokens = set(normalized.split())
    if "status" in tokens or "state" in tokens:
        return True

    return "workflow" in tokens and ("status" in tokens or "state" in tokens)


def _first_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    contexts = list(contexts)
    explicit = _first_text(contexts, _EXPLICIT_STATUS_KEYS)
    if explicit:
        return explicit

    changed = _first_changed_status(contexts)
    if changed:
        return changed

    return _first_text(contexts, _CURRENT_STATUS_KEYS)


def _first_changed_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        for key in ("changes", "changedFields"):
            status = _status_from_change(context.get(key))
            if status:
                return status
    return None


def _status_from_change(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for field, change in value.items():
            if _looks_like_status_field(field):
                return _first_text([change], _CHANGED_STATUS_VALUE_KEYS) or _extract_text(change)
        return None

    if isinstance(value, str):
        return None

    if isinstance(value, Iterable):
        for item in value:
            if not isinstance(item, Mapping):
                continue

            field = _first_text([item], ("field", "fieldName", "field_name", "key", "name"))
            if _looks_like_status_field(field):
                status = _first_text([item], _CHANGED_STATUS_VALUE_KEYS)
                if status:
                    return status

    return None


def _first_text(contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for context in contexts:
        for key in keys:
            value = _extract_text(context.get(key))
            if value:
                return value
    return None


def _extract_text(value: Any) -> str | None:
    if isinstance(value, str):
        text = value.strip()
        return text or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "value", "identifier", "key", "id"):
            text = _extract_text(value.get(key))
            if text:
                return text

    return None


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())


def _normalize(value: Any) -> str:
    text = _extract_text(value)
    if not text:
        return ""

    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.casefold().split())


def main() -> int:
    """Read a JSON event from stdin and print the update action, if any."""

    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
