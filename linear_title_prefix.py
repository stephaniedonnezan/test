"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"

_TRIGGER_KEYS = ("trigger", "webhookType", "action", "type", "eventType")
_DIRECT_STATUS_CHANGE_EVENTS = {
    "status changed",
    "status change",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow status changed",
    "issue status changed",
}
_GENERIC_UPDATE_EVENTS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}
_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "state id",
    "workflow state",
    "workflow state id",
    "workflow status",
    "workflow status id",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title-update action when an issue moves to To Research.

    The automation payload can arrive as a flat Cursor ``triggerContext`` object,
    wrapped under ``automation_trigger_info.triggerContext``, or as a nested
    Linear webhook shape. This function keeps the contract small: it returns the
    action the runner can apply, or ``None`` when no title change is needed.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = list(_payload_contexts(event))
    if not _is_status_change_event(contexts):
        return None

    new_status = _status_from_contexts(contexts)
    if _normalize_text(new_status) != RESEARCH_STATUS:
        return None

    title = _first_text(contexts, ("title", "issueTitle", "issue_title"))
    issue_id = _first_text(
        contexts,
        ("issueId", "issue_id", "identifier", "key", "id"),
    )

    if not issue_id or not title:
        return None

    stripped_title = title.strip()
    if not stripped_title:
        return None
    if stripped_title.casefold().startswith(TITLE_PREFIX.casefold()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {stripped_title}",
    }


def _payload_contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely metadata and issue objects in priority order."""

    seen: set[int] = set()

    def add(value: Any) -> Mapping[str, Any] | None:
        if isinstance(value, Mapping) and id(value) not in seen:
            seen.add(id(value))
            return value
        return None

    def walk(value: Any) -> Iterable[Mapping[str, Any]]:
        context = add(value)
        if context is None:
            return

        yield context
        for key in ("data", "issue", "state", "workflowState", "workflowStatus"):
            yield from walk(context.get(key))

    yield from walk(event.get("triggerContext"))

    automation_info = event.get("automation_trigger_info") or event.get(
        "automationTriggerInfo"
    )
    if isinstance(automation_info, Mapping):
        yield from walk(automation_info.get("triggerContext"))

    yield from walk(event)


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    trigger_names = [
        normalized
        for context in contexts
        for key in _TRIGGER_KEYS
        if (normalized := _normalize_text(context.get(key)))
    ]

    if any(name in _DIRECT_STATUS_CHANGE_EVENTS for name in trigger_names):
        return True

    has_generic_update = any(name in _GENERIC_UPDATE_EVENTS for name in trigger_names)
    return has_generic_update and _changed_fields_include_status(contexts)


def _changed_fields_include_status(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            fields = context.get(key)
            if _field_collection_includes_status(fields):
                return True

        for key in ("changes", "updatedFrom", "updated_from", "previousValues"):
            changes = context.get(key)
            if isinstance(changes, Mapping) and any(
                _is_status_field(field_name) for field_name in changes
            ):
                return True

    return False


def _field_collection_includes_status(fields: Any) -> bool:
    if isinstance(fields, str):
        return _is_status_field(fields)

    if isinstance(fields, Mapping):
        return any(_is_status_field(field_name) for field_name in fields)

    if isinstance(fields, Iterable):
        for field in fields:
            if isinstance(field, Mapping):
                name = _first_text([field], ("name", "field", "fieldName", "key"))
                if name and _is_status_field(name):
                    return True
            elif _is_status_field(field):
                return True

    return False


def _is_status_field(field_name: Any) -> bool:
    normalized = _normalize_text(field_name)
    return normalized in _STATUS_FIELD_NAMES


def _status_from_contexts(contexts: list[Mapping[str, Any]]) -> str | None:
    explicit = _first_text(
        contexts,
        (
            "newStatus",
            "new_status",
            "newStatusName",
            "new_status_name",
            "toStatus",
            "to_status",
            "statusName",
            "status_name",
        ),
    )
    if explicit:
        return explicit

    for context in contexts:
        status = context.get("status")
        if isinstance(status, Mapping):
            value = _first_text([status], ("name", "title"))
            if value:
                return value
        elif isinstance(status, str):
            return status

        for key in ("state", "workflowState", "workflowStatus"):
            value = context.get(key)
            if isinstance(value, Mapping):
                name = _first_text([value], ("name", "title"))
                if name:
                    return name
            elif isinstance(value, str):
                return value

    return None


def _first_text(contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value
            if isinstance(value, int):
                return str(value)
    return None


def _normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    words = re.sub(r"[^A-Za-z0-9]+", " ", separated).casefold().split()
    return " ".join(words)


def main() -> int:
    payload = json.load(sys.stdin)
    result = build_issue_title_update(payload)
    print(json.dumps(result, sort_keys=True) if result else "null")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
