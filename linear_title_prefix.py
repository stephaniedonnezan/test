"""Build Linear issue title updates for Cursor research automations."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


CURSOR_RESEARCHING_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_CHANGED_TRIGGER = "status_changed"


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update when a Linear issue moves to the research status.

    The automation payload can provide issue fields either at the top level or
    inside ``triggerContext``. This function keeps the decision side-effect free
    so the caller can apply the returned action with its Linear client.
    """

    if not isinstance(event, Mapping):
        return None

    context = event.get("triggerContext")
    if not isinstance(context, Mapping):
        context = event

    if _normalize_trigger(context.get("trigger")) != STATUS_CHANGED_TRIGGER:
        return None

    status = context.get("newStatus", context.get("status"))
    if _normalize_status(status) != TARGET_STATUS:
        return None

    raw_title = context.get("title", event.get("title"))
    if not isinstance(raw_title, str):
        return None

    title = raw_title.strip()
    if not title or _has_cursor_researching_prefix(title):
        return None

    issue_id = context.get("id", context.get("issueId", event.get("id", event.get("issueId"))))
    if not isinstance(issue_id, str) or not issue_id.strip():
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{CURSOR_RESEARCHING_PREFIX}: {title}",
    }


def _normalize_trigger(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[\s-]+", "_", value.strip().lower())


def _normalize_status(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[\s_-]+", " ", value.strip().lower())


def _has_cursor_researching_prefix(title: str) -> bool:
    return title.lower().startswith(CURSOR_RESEARCHING_PREFIX.lower())
