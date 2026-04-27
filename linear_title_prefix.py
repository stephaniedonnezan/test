"""Build title update actions for Linear issue status-change webhooks."""

from __future__ import annotations

import re
from typing import Any, Mapping


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_CHANGED_TRIGGER = "status changed"


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when an issue moves to the research status."""

    payload = _trigger_context(event)

    if _normalize(payload.get("trigger")) != STATUS_CHANGED_TRIGGER:
        return None

    new_status = payload.get("newStatus", payload.get("status"))
    if _normalize(new_status) != TARGET_STATUS:
        return None

    title = _string_value(payload.get("title"))
    issue_id = _string_value(payload.get("id") or payload.get("issueId"))
    if not title or not issue_id or _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _trigger_context(event: Mapping[str, Any]) -> Mapping[str, Any]:
    context = event.get("triggerContext")
    if isinstance(context, Mapping):
        return context
    return event


def _normalize(value: Any) -> str:
    normalized = _string_value(value).casefold()
    return re.sub(r"[\s_-]+", " ", normalized).strip()


def _string_value(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    return ""


def _has_prefix(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())
