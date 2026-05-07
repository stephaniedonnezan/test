"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TITLE_PREFIX_WITH_SEPARATOR = f"{TITLE_PREFIX}: "
TARGET_STATUS = "to research"
STATUS_CHANGE_TRIGGERS = {
    "status change",
    "status changed",
    "state change",
    "state changed",
}
ISSUE_UPDATED_TRIGGERS = {
    "issue update",
    "issue updated",
}
STATUS_FIELD_NAMES = {"status", "state"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title-update action for issues moved to to research."""
    if not isinstance(event, Mapping):
        return None

    contexts = _context_chain(event)
    if not _is_status_change_event(contexts):
        return None

    status = _first_normalized_status(contexts)
    if status != TARGET_STATUS:
        return None

    issue_id = _first_string(contexts, ("id", "issueId", "issue_id", "identifier"))
    title = _first_string(contexts, ("title",))
    if not issue_id or not title:
        return None

    title = title.strip()
    if not title or _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX_WITH_SEPARATOR}{title}",
    }


def _context_chain(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = [event]

    for path in (
        ("triggerContext",),
        ("triggerContext", "data"),
        ("triggerContext", "data", "issue"),
        ("triggerContext", "issue"),
        ("data",),
        ("data", "issue"),
        ("issue",),
    ):
        context = _nested_mapping(event, path)
        if context is not None:
            contexts.append(context)

    return contexts


def _nested_mapping(
    value: Mapping[str, Any], path: tuple[str, ...]
) -> Mapping[str, Any] | None:
    current: Any = value
    for key in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current if isinstance(current, Mapping) else None


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        trigger = _first_string([context], ("trigger", "action", "type"))
        normalized_trigger = _normalize_text(trigger)
        if normalized_trigger in STATUS_CHANGE_TRIGGERS:
            return True
        if normalized_trigger in ISSUE_UPDATED_TRIGGERS and _updated_status_field(context):
            return True
    return False


def _updated_status_field(context: Mapping[str, Any]) -> bool:
    updated_fields = context.get("updatedFields")
    if not isinstance(updated_fields, list):
        return False

    for field in updated_fields:
        if _normalize_text(str(field)) in STATUS_FIELD_NAMES:
            return True
    return False


def _first_normalized_status(contexts: list[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        status = _status_from_context(context)
        if status:
            return _normalize_text(status)
    return None


def _status_from_context(context: Mapping[str, Any]) -> str | None:
    status = _first_string([context], ("newStatus", "new_status", "status"))
    if status:
        return status

    state = context.get("state")
    if isinstance(state, Mapping):
        return _first_string([state], ("name", "title"))

    return None


def _first_string(
    contexts: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...],
    keys: tuple[str, ...],
) -> str | None:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None

    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value.strip())
    separated = re.sub(r"[-_]+", " ", separated)
    return re.sub(r"\s+", " ", separated).lower()


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())
