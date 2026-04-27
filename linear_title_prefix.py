"""Build Linear issue title updates for research status transitions."""

from __future__ import annotations

import re
from typing import Any, Mapping


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_CHANGED_TRIGGER = "status changed"


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when an issue moves to To Research."""

    context = _trigger_context(event)
    if _normalize(context.get("trigger")) != STATUS_CHANGED_TRIGGER:
        return None

    status = context.get("newStatus", context.get("status"))
    if _normalize(status) != TARGET_STATUS:
        return None

    title = context.get("title")
    issue_id = context.get("id") or context.get("issueId")
    if not isinstance(title, str) or not title.strip() or not issue_id:
        return None

    if _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": str(issue_id),
        "title": f"{PREFIX}: {title}",
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


def _has_prefix(title: str) -> bool:
    return title.casefold().lstrip().startswith(PREFIX.casefold())
