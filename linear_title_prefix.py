"""Build Linear title updates for issues entering research.

The automation runner can pass either the flat Cursor trigger context or a
nested Linear webhook-style payload. This module keeps the output intentionally
small so the caller can decide how to execute the returned action.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


ACTION = "update_issue_title"
PREFIX = "Cursor researching"
TARGET_STATUS = "to research"


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear issue title update action when the event should be handled."""
    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_change(contexts):
        return None

    new_status = _new_status(contexts)
    if _normalize_label(new_status) != TARGET_STATUS:
        return None

    issue_id = _issue_id(contexts)
    title = _first_text(contexts, ("title", "name"))
    if not issue_id or not title or _has_prefix(title):
        return None

    return {
        "action": ACTION,
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def handle_issue_status_changed(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Compatibility alias for automation runners using handler-style naming."""
    return build_issue_title_update(event)


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return likely event/issue dictionaries with outer metadata first."""
    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)

    add(event.get("triggerContext"))
    add(event)

    data = event.get("data")
    add(data)
    if isinstance(data, Mapping):
        add(data.get("issue"))

    add(event.get("issue"))

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        add(trigger_context.get("data"))
        add(trigger_context.get("issue"))

    return contexts


def _is_status_change(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("trigger", "action", "type", "webhookType"):
            trigger = _normalize_compact(context.get(key))
            if trigger in {"statuschanged", "statuschange"}:
                return True

    for context in contexts:
        for key in ("updatedFields", "changedFields"):
            if _contains_status_field(context.get(key)):
                return True

        changes = context.get("changes")
        if isinstance(changes, Mapping) and any(_is_status_field(key) for key in changes):
            return True

        updated_from = context.get("updatedFrom")
        if isinstance(updated_from, Mapping) and any(_is_status_field(key) for key in updated_from):
            return True

    return False


def _new_status(contexts: list[Mapping[str, Any]]) -> Any:
    explicit_keys = (
        "newStatus",
        "new_status",
        "newStatusName",
        "new_status_name",
        "toStatus",
        "to_status",
        "toState",
        "to_state",
    )
    status_keys = ("status", "state", "workflowState")

    for context in contexts:
        for key in explicit_keys:
            value = _extract_name(context.get(key))
            if value:
                return value

    for context in contexts:
        changes = context.get("changes")
        if isinstance(changes, Mapping):
            for key in ("status", "state", "workflowState"):
                value = _changed_to_value(changes.get(key))
                if value:
                    return value

    for context in contexts:
        for key in status_keys:
            value = _extract_name(context.get(key))
            if value:
                return value

    return None


def _changed_to_value(change: Any) -> Any:
    if isinstance(change, Mapping):
        for key in ("newValue", "new_value", "to", "after", "name"):
            value = _extract_name(change.get(key))
            if value:
                return value
    return _extract_name(change)


def _extract_name(value: Any) -> Any:
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            text = _text(value.get(key))
            if text:
                return text
    return value


def _first_text(contexts: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for context in contexts:
        for key in keys:
            text = _text(context.get(key))
            if text:
                return text
    return None


def _issue_id(contexts: list[Mapping[str, Any]]) -> str | None:
    identifier = _first_text(contexts, ("issueId", "issue_id", "identifier", "key"))
    if identifier:
        return identifier

    for context in contexts:
        if _text(context.get("title")) or _text(context.get("name")):
            issue_id = _text(context.get("id"))
            if issue_id:
                return issue_id

    return _first_text(contexts, ("id",))


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)
    if isinstance(value, Mapping):
        return any(_is_status_field(key) or _is_status_field(item) for key, item in value.items())
    if isinstance(value, (list, tuple, set)):
        return any(_contains_status_field(item) for item in value)
    return False


def _is_status_field(value: Any) -> bool:
    normalized = _normalize_compact(value)
    return normalized in {"status", "state", "workflowstate", "stateid", "workflowstateid"}


def _normalize_label(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def _normalize_compact(value: Any) -> str:
    label = _normalize_label(value)
    return label.replace(" ", "") if label else ""


def main() -> int:
    event = json.load(sys.stdin)
    result = build_issue_title_update(event)
    if result is not None:
        print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
