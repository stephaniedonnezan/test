"""Helpers for adding a Cursor research prefix to Linear issue titles."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Build an issue-title update action for Linear "to research" transitions.

    The automation payload has historically appeared both as a flat object and
    under ``triggerContext``. This helper accepts either shape and returns a
    side-effect-free action object for the caller to apply.
    """
    if not isinstance(event, Mapping):
        return None

    context = _get_trigger_context(event)
    if _normalize(context.get("trigger")) != "status changed":
        return None

    new_status = context.get("newStatus", context.get("status"))
    if _normalize(new_status) != "to research":
        return None

    issue_id = context.get("id", context.get("issueId"))
    title = context.get("title")
    if not issue_id or not isinstance(title, str):
        return None

    clean_title = title.strip()
    if not clean_title or _has_research_prefix(clean_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": str(issue_id),
        "title": f"{TITLE_PREFIX}: {clean_title}",
    }


def _get_trigger_context(event: Mapping[str, Any]) -> Mapping[str, Any]:
    context = event.get("triggerContext")
    return context if isinstance(context, Mapping) else event


def _normalize(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"[\s_-]+", " ", str(value).strip().lower())


def _has_research_prefix(title: str) -> bool:
    return _normalize(title).startswith(_normalize(TITLE_PREFIX))
