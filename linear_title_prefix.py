"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


CURSOR_RESEARCHING_PREFIX = "Cursor researching"
UPDATE_ISSUE_TITLE_ACTION = "update_issue_title"
_TARGET_STATUS = "to research"
_TARGET_TRIGGER = "status changed"


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update payload when a Linear issue moves to To Research."""

    if not isinstance(event, Mapping):
        return None

    context = _trigger_context(event)
    if _normalize(context.get("trigger")) != _TARGET_TRIGGER:
        return None

    new_status = context.get("newStatus") or context.get("status")
    if _normalize(new_status) != _TARGET_STATUS:
        return None

    issue_id = (
        _string_value(context, "id")
        or _string_value(context, "issueId")
        or _string_value(event, "id")
        or _string_value(event, "issueId")
    )
    title = _string_value(context, "title") or _string_value(event, "title")
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_cursor_researching_prefix(title):
        return None

    return {
        "action": UPDATE_ISSUE_TITLE_ACTION,
        "issueId": issue_id,
        "title": f"{CURSOR_RESEARCHING_PREFIX}: {title}",
    }


def _trigger_context(event: Mapping[str, Any]) -> Mapping[str, Any]:
    context = event.get("triggerContext")
    return context if isinstance(context, Mapping) else event


def _string_value(mapping: Mapping[str, Any], key: str) -> str:
    value = mapping.get(key)
    return value.strip() if isinstance(value, str) else ""


def _normalize(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def _has_cursor_researching_prefix(title: str) -> bool:
    return title.casefold().startswith(CURSOR_RESEARCHING_PREFIX.casefold())
