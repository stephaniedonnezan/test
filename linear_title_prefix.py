"""Build Linear issue title updates for research-status automations."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update when an issue moves to "to research"."""
    if not isinstance(event, Mapping):
        return None

    context = _trigger_context(event)
    if _normalize(context.get("trigger")) != "status changed":
        return None

    status = context.get("newStatus", context.get("status"))
    if _normalize(status) != TARGET_STATUS:
        return None

    issue_id = _string_value(context.get("id") or context.get("issueId"))
    title = _string_value(context.get("title"))
    if issue_id is None or title is None:
        return None

    stripped_title = title.strip()
    if _has_prefix(stripped_title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id,
        "title": f"{PREFIX}: {stripped_title}",
    }


def _trigger_context(event: Mapping[str, Any]) -> Mapping[str, Any]:
    context = event.get("triggerContext")
    return context if isinstance(context, Mapping) else event


def _normalize(value: Any) -> str | None:
    text = _string_value(value)
    if text is None:
        return None

    return re.sub(r"[\s_-]+", " ", text.strip().casefold())


def _string_value(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    return value if value.strip() else None


def _has_prefix(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())
