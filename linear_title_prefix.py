"""Build Linear issue title updates for research status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow state"}
DIRECT_STATUS_CHANGE_EVENTS = {
    "status changed",
    "status change",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
}
GENERIC_UPDATE_EVENTS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an update action when a Linear issue moves to "to research"."""
    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_change_event(contexts):
        return None

    new_status = _first_text(
        contexts,
        ("newStatus", "new_status", "status", "state", "workflowState", "workflow_state"),
    )
    if _normalize(new_status) != TARGET_STATUS:
        return None

    issue_id = _first_text(contexts, ("issueId", "issue_id", "id", "identifier", "key"))
    title = _first_text(contexts, ("title", "name"))
    if not issue_id or not title:
        return None

    issue_id = issue_id.strip()
    title = title.strip()
    if not issue_id or not title or _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return relevant payload dictionaries from outermost to innermost."""
    contexts: list[Mapping[str, Any]] = []
    stack: list[Any] = [event]
    seen: set[int] = set()

    while stack:
        current = stack.pop(0)
        if not isinstance(current, Mapping) or id(current) in seen:
            continue

        seen.add(id(current))
        contexts.append(current)

        for key in ("automation_trigger_info", "triggerContext", "trigger_context", "data", "issue"):
            value = current.get(key)
            if isinstance(value, Mapping):
                stack.append(value)

    return contexts


def _is_status_change_event(contexts: Sequence[Mapping[str, Any]]) -> bool:
    event_names: list[str] = []
    for context in contexts:
        for key in ("trigger", "webhookType", "webhook_type", "action", "type"):
            event_names.extend(_text_values(context.get(key)))

    if any(_normalize(name) in DIRECT_STATUS_CHANGE_EVENTS for name in event_names):
        return True

    if any(_normalize(name) in GENERIC_UPDATE_EVENTS for name in event_names):
        return _has_status_field_change(contexts)

    return False


def _has_status_field_change(contexts: Sequence[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            if _contains_status_field(context.get(key)):
                return True

        changes = context.get("changes")
        if isinstance(changes, Mapping) and _contains_status_field(changes.keys()):
            return True

        updated_from = context.get("updatedFrom") or context.get("updated_from")
        if isinstance(updated_from, Mapping) and _contains_status_field(updated_from.keys()):
            return True

    return False


def _contains_status_field(value: Any) -> bool:
    return any(_normalize_field_name(item) in STATUS_FIELD_NAMES for item in _text_values(value))


def _first_text(contexts: Sequence[Mapping[str, Any]], keys: Sequence[str]) -> str | None:
    for key in keys:
        for context in contexts:
            if key not in context:
                continue

            value = context[key]
            text = _extract_text(value)
            if text:
                return text

    return None


def _extract_text(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None

    if isinstance(value, (int, float)):
        return str(value)

    if isinstance(value, Mapping):
        for key in ("name", "title", "id", "identifier", "key"):
            text = _extract_text(value.get(key))
            if text:
                return text

    return None


def _text_values(value: Any) -> list[str]:
    if value is None:
        return []

    if isinstance(value, str):
        return [value]

    if isinstance(value, Mapping):
        return [str(key) for key in value.keys()]

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        values: list[str] = []
        for item in value:
            values.extend(_text_values(item))
        return values

    return [str(value)]


def _normalize(value: Any) -> str:
    text = "" if value is None else str(value)
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[_\-/]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()


def _normalize_field_name(value: Any) -> str:
    return _normalize(value).replace(" ", "")


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
