"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue title update action for Linear research transitions."""
    if not isinstance(event, Mapping):
        return None

    context = _trigger_context(event)
    if _normalize_token(context.get("trigger")) != "status changed":
        return None

    status = context.get("newStatus", context.get("status"))
    if _normalize_token(status) != TARGET_STATUS:
        return None

    issue_id = _first_text(
        context.get("id"),
        context.get("issueId"),
        _mapping_value(context.get("issue"), "id"),
        _mapping_value(event.get("issue"), "id"),
        event.get("id"),
        event.get("issueId"),
    )
    title = _first_text(
        context.get("title"),
        _mapping_value(context.get("issue"), "title"),
        _mapping_value(event.get("issue"), "title"),
        event.get("title"),
    )

    if issue_id is None or title is None or _has_research_prefix(title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id,
        "title": f"{PREFIX}: {title.strip()}",
    }


def _trigger_context(event: Mapping[str, Any]) -> Mapping[str, Any]:
    context = event.get("triggerContext")
    return context if isinstance(context, Mapping) else event


def _mapping_value(value: Any, key: str) -> Any:
    return value.get(key) if isinstance(value, Mapping) else None


def _first_text(*values: Any) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _normalize_token(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return re.sub(r"[\s_-]+", " ", value.strip().casefold())


def _has_research_prefix(title: str) -> bool:
    return title.strip().casefold().startswith(PREFIX.casefold())
