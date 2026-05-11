"""Helpers for deriving Linear issue title updates from automation events."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


RESEARCH_STATUS = "to research"
RESEARCH_TITLE_PREFIX = "Cursor researching"


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action for Linear issues that move to research.

    The Cursor automation payload currently exposes Linear details under
    ``triggerContext``, but accepting a flat mapping keeps the helper simple to
    test and safe to call from small webhook adapters.
    """

    if not isinstance(event, Mapping):
        return None

    payload = _payload_from_event(event)
    if not payload:
        return None

    if _normalize(payload.get("trigger")) != "status_changed":
        return None

    status = payload.get("newStatus", payload.get("status"))
    if _normalize(status) != RESEARCH_STATUS:
        return None

    issue_id = payload.get("id") or payload.get("issueId")
    if not isinstance(issue_id, str) or not issue_id.strip():
        return None

    title = payload.get("title")
    if not isinstance(title, str) or not title.strip():
        return None

    stripped_title = title.strip()
    if _has_research_prefix(stripped_title):
        updated_title = stripped_title
    else:
        updated_title = f"{RESEARCH_TITLE_PREFIX}: {stripped_title}"

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": updated_title,
    }


def _payload_from_event(event: Mapping[str, Any]) -> Mapping[str, Any] | None:
    trigger_context = event.get("triggerContext")
    if trigger_context is None:
        return event
    if isinstance(trigger_context, Mapping):
        return trigger_context
    return None


def _normalize(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return " ".join(value.strip().casefold().split())


def _has_research_prefix(title: str) -> bool:
    normalized_title = _normalize(title)
    normalized_prefix = _normalize(RESEARCH_TITLE_PREFIX)
    if normalized_title is None or normalized_prefix is None:
        return False
    return normalized_title == normalized_prefix or normalized_title.startswith(
        f"{normalized_prefix}:"
    )
