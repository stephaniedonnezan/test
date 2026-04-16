"""Helpers for updating Linear issue titles from status changes."""

from __future__ import annotations

from typing import Any

RESEARCH_STATUS = "to research"
RESEARCH_PREFIX = "Cursor researching"


def add_researching_to_issue_title(
    title: str,
    new_status: str,
    *,
    prefix: str = RESEARCH_PREFIX,
    separator: str = " - ",
) -> str:
    """Add a research marker to the issue title when status is `to research`."""
    if not isinstance(title, str):
        raise TypeError("title must be a string")

    if not isinstance(new_status, str) or new_status.strip().casefold() != RESEARCH_STATUS:
        return title

    if prefix.casefold() in title.casefold():
        return title

    if not title:
        return prefix

    return f"{prefix}{separator}{title}"


def apply_status_change_to_issue_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of payload with updated title for Linear status changes."""
    updated_payload = dict(payload)
    trigger_context = payload.get("triggerContext")

    if not isinstance(trigger_context, dict):
        return updated_payload

    if trigger_context.get("triggerType") != "linear":
        return updated_payload

    if trigger_context.get("trigger") != "status_changed":
        return updated_payload

    current_title = trigger_context.get("title")
    new_status = trigger_context.get("newStatus")

    if not isinstance(current_title, str):
        return updated_payload

    updated_title = add_researching_to_issue_title(current_title, str(new_status or ""))
    if updated_title == current_title:
        return updated_payload

    updated_trigger_context = dict(trigger_context)
    updated_trigger_context["title"] = updated_title
    updated_payload["triggerContext"] = updated_trigger_context

    return updated_payload
