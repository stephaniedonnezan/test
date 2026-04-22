"""Helpers for processing Linear issue webhook payloads."""

from __future__ import annotations

from typing import Any

RESEARCH_PREFIX = "Cursor researching"


def _normalize_status(value: Any) -> str:
    """Return a normalized status string."""
    if value is None:
        return ""
    return str(value).strip().casefold()


def title_with_research_prefix(title: str) -> str:
    """Add the research prefix to a title if not present."""
    clean_title = (title or "").strip()
    if clean_title.casefold().startswith(RESEARCH_PREFIX.casefold()):
        return clean_title
    if not clean_title:
        return RESEARCH_PREFIX
    return f"{RESEARCH_PREFIX} - {clean_title}"


def updated_title_for_status_change(event_payload: dict[str, Any]) -> str | None:
    """
    Return the updated issue title when a status change needs it.

    Behavior:
    - When triggerContext.trigger == "status_changed"
    - And triggerContext.newStatus == "to research" (case-insensitive)
    - Return title with the "Cursor researching" prefix (idempotent)
    - Otherwise return None
    """
    trigger_context = event_payload.get("triggerContext")
    if not isinstance(trigger_context, dict):
        return None

    if trigger_context.get("trigger") != "status_changed":
        return None

    if _normalize_status(trigger_context.get("newStatus")) != "to research":
        return None

    title = trigger_context.get("title")
    if not isinstance(title, str):
        title = ""

    new_title = title_with_research_prefix(title)
    return new_title if new_title != title else None


def apply_issue_title_rules(event_payload: dict[str, Any]) -> dict[str, Any]:
    """
    Return a payload copy with title rules applied.

    Current rule:
    - On status_changed -> to research, prefix title with "Cursor researching".
    """
    updated_payload = dict(event_payload)
    trigger_context = updated_payload.get("triggerContext")
    if not isinstance(trigger_context, dict):
        return updated_payload

    updated_context = dict(trigger_context)
    updated_title = updated_title_for_status_change(updated_payload)
    if updated_title is not None:
        updated_context["title"] = updated_title
        updated_payload["triggerContext"] = updated_context

    return updated_payload
