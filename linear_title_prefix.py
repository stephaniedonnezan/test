"""Build Linear issue title updates for Cursor research automation."""

from __future__ import annotations

import re
from typing import Any, Mapping


PREFIX = "Cursor researching"
PREFIXED_TITLE = f"{PREFIX}: "
TARGET_STATUS = "to research"
STATUS_CHANGED_TRIGGER = "status changed"


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to research."""
    payload = _trigger_context(event)

    if _normalize(payload.get("trigger")) != STATUS_CHANGED_TRIGGER:
        return None

    new_status = payload.get("newStatus", payload.get("status"))
    if _normalize(new_status) != TARGET_STATUS:
        return None

    issue_id = _string_or_none(payload.get("id") or payload.get("issueId"))
    title = _string_or_none(payload.get("title"))
    if issue_id is None or title is None:
        return None

    stripped_title = title.strip()
    if _already_prefixed(stripped_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIXED_TITLE}{stripped_title}",
    }


def _trigger_context(event: Mapping[str, Any]) -> Mapping[str, Any]:
    context = event.get("triggerContext")
    if isinstance(context, Mapping):
        return context
    return event


def _normalize(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[\s_-]+", " ", value).strip().casefold()


def _string_or_none(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value or None


def _already_prefixed(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())
