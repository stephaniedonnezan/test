"""Build Linear issue title updates for issues entering research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_CAMEL_CASE_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_NON_ALNUM = re.compile(r"[^a-z0-9]+")
_STATUS_FIELD_NAMES = {"status", "state", "workflow state", "workflowstate"}
_TRIGGER_KEYS = {"trigger", "webhookType", "action", "type", "eventType", "triggerType"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear issue title update action when an issue enters research.

    The automation runner supplies a flat ``triggerContext`` payload, while
    Linear webhooks are commonly nested under ``data`` and ``issue``. This
    function accepts both shapes and returns a small action object that callers
    can translate into an API update.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = list(_candidate_contexts(event))
    if not _is_status_change_event(contexts):
        return None

    status = _extract_status(contexts)
    if _normalize(status) != TARGET_STATUS:
        return None

    title = _first_text(contexts, ("title", "name"))
    if not title:
        return None

    stripped_title = title.strip()
    if _has_prefix(stripped_title):
        return None

    issue_id = _extract_issue_id(contexts)
    if not issue_id:
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {stripped_title}",
    }


def _candidate_contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely metadata and issue objects from outermost to innermost."""

    seen: set[int] = set()

    def visit(value: Any) -> Iterable[Mapping[str, Any]]:
        if not isinstance(value, Mapping) or id(value) in seen:
            return

        seen.add(id(value))
        yield value

        for key in (
            "triggerContext",
            "payload",
            "data",
            "issue",
            "node",
            "state",
            "status",
            "workflowState",
            "workflow_state",
        ):
            child = value.get(key)
            if isinstance(child, Mapping):
                yield from visit(child)

    yield from visit(event)


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    trigger_values: list[str] = []
    for context in contexts:
        for key, value in context.items():
            if key in _TRIGGER_KEYS:
                text = _text_value(value)
                if text:
                    trigger_values.append(_normalize(text))

    if any(_is_direct_status_trigger(value) for value in trigger_values):
        return True

    if any(_is_update_trigger(value) for value in trigger_values):
        return _mentions_status_field(contexts)

    return False


def _is_direct_status_trigger(value: str) -> bool:
    return value in {
        "status changed",
        "status change",
        "state changed",
        "state change",
        "workflow state changed",
        "workflow state change",
    }


def _is_update_trigger(value: str) -> bool:
    return value in {
        "update",
        "updated",
        "issue update",
        "issue updated",
        "updated issue",
    }


def _mentions_status_field(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in (
            "updatedFields",
            "updated_fields",
            "changedFields",
            "changed_fields",
            "changes",
        ):
            value = context.get(key)
            if _value_mentions_status_field(value):
                return True
    return False


def _value_mentions_status_field(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(_normalize(str(key)) in _STATUS_FIELD_NAMES for key in value)

    if isinstance(value, str):
        return _normalize(value) in _STATUS_FIELD_NAMES

    if isinstance(value, Iterable):
        for item in value:
            if isinstance(item, Mapping):
                names = (item.get("name"), item.get("field"), item.get("key"))
                if any(_normalize(str(name)) in _STATUS_FIELD_NAMES for name in names if name):
                    return True
            elif _normalize(str(item)) in _STATUS_FIELD_NAMES:
                return True

    return False


def _extract_status(contexts: list[Mapping[str, Any]]) -> str | None:
    for key in ("newStatus", "new_status", "statusName", "stateName", "workflowStateName"):
        value = _first_text(contexts, (key,))
        if value:
            return value

    for key in ("status", "state", "workflowState", "workflow_state"):
        value = _first_text(contexts, (key,))
        if value:
            return value

    return None


def _extract_issue_id(contexts: list[Mapping[str, Any]]) -> str | None:
    for key in ("issueId", "issue_id", "identifier", "key", "id"):
        value = _first_text(contexts, (key,))
        if value:
            return value.strip()
    return None


def _first_text(contexts: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            text = _text_value(value)
            if text and text.strip():
                return text.strip()
    return None


def _text_value(value: Any) -> str | None:
    if isinstance(value, str):
        return value

    if isinstance(value, Mapping):
        for key in ("name", "title", "identifier", "key", "id"):
            nested = value.get(key)
            if isinstance(nested, str) and nested.strip():
                return nested

    return None


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def _normalize(value: str | None) -> str | None:
    if value is None:
        return None

    spaced = _CAMEL_CASE_BOUNDARY.sub(" ", str(value))
    return _NON_ALNUM.sub(" ", spaced.lower()).strip()


def main() -> int:
    """Read a JSON event from stdin and print the requested action as JSON."""

    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    action = build_issue_title_update(event)
    print(json.dumps(action, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
