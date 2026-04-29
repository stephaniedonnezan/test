"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
PREFIXED_TITLE = f"{TITLE_PREFIX}: {{title}}"


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title-update action when a Linear issue moves to research."""
    if not isinstance(event, Mapping):
        return None

    context = _trigger_context(event)
    if _normalize(context.get("trigger")) != "status changed":
        return None

    status = context.get("newStatus", context.get("status"))
    if _normalize(status) != "to research":
        return None

    issue_id = _text(context.get("id", context.get("issueId")))
    title = _text(context.get("title"))
    if not issue_id or not title:
        return None

    if title.casefold().startswith(TITLE_PREFIX.casefold()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": PREFIXED_TITLE.format(title=title),
    }


def _trigger_context(event: Mapping[str, Any]) -> Mapping[str, Any]:
    context = event.get("triggerContext")
    if isinstance(context, Mapping):
        return context
    return event


def _normalize(value: Any) -> str:
    text = _text(value).casefold()
    text = re.sub(r"[_-]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    return ""
