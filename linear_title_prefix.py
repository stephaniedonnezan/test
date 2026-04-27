"""Helpers for Linear issue title updates triggered by status changes."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


CURSOR_RESEARCHING_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_CHANGED_TRIGGER = "status changed"


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update action when an issue enters research."""

    if not isinstance(event, Mapping):
        return None

    context = _trigger_context(event)
    if _normalize(context.get("trigger")) != STATUS_CHANGED_TRIGGER:
        return None

    new_status = context.get("newStatus", context.get("status"))
    if _normalize(new_status) != TARGET_STATUS:
        return None

    title = _string_value(context.get("title"))
    issue_id = _string_value(context.get("id") or context.get("issueId"))
    if not title.strip() or not issue_id or _has_researching_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{CURSOR_RESEARCHING_PREFIX}: {title.strip()}",
    }


def _trigger_context(event: Mapping[str, Any]) -> Mapping[str, Any]:
    trigger_context = event.get("triggerContext")
    return trigger_context if isinstance(trigger_context, Mapping) else event


def _normalize(value: Any) -> str:
    text = _string_value(value)
    text = re.sub(r"[_-]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip().casefold()


def _string_value(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _has_researching_prefix(title: str) -> bool:
    return title.lstrip().casefold().startswith(CURSOR_RESEARCHING_PREFIX.casefold())
