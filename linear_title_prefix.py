"""Helpers for Linear issue title updates triggered by status changes."""

from __future__ import annotations

import re
from typing import Any, Mapping


CURSOR_RESEARCHING_PREFIX = "Cursor researching"
_TARGET_STATUS = "to research"
_TARGET_TRIGGER = "status changed"


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update payload when an issue moves to To Research.

    The automation receives Linear trigger details either directly on the
    payload or nested under ``triggerContext``. Only status-change events whose
    new status is "to research" should add the Cursor researching prefix.
    """

    trigger_context = _mapping_value(event, "triggerContext") or event
    trigger = _string_value(trigger_context, "trigger")
    status = _string_value(trigger_context, "newStatus") or _string_value(
        trigger_context, "status"
    )

    if _normalize(trigger) != _TARGET_TRIGGER or _normalize(status) != _TARGET_STATUS:
        return None

    issue_id = _string_value(trigger_context, "id") or _string_value(event, "id")
    title = _string_value(trigger_context, "title") or _string_value(event, "title")
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_cursor_researching_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{CURSOR_RESEARCHING_PREFIX}: {title}",
    }


def _mapping_value(mapping: Mapping[str, Any], key: str) -> Mapping[str, Any] | None:
    value = mapping.get(key)
    return value if isinstance(value, Mapping) else None


def _string_value(mapping: Mapping[str, Any], key: str) -> str:
    value = mapping.get(key)
    return value.strip() if isinstance(value, str) else ""


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _has_cursor_researching_prefix(title: str) -> bool:
    return title.lower().startswith(CURSOR_RESEARCHING_PREFIX.lower())
