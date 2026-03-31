"""Utilities to update Linear issue titles for research status transitions."""

from __future__ import annotations

from typing import Any, Dict, Optional

RESEARCH_PREFIX = "Cursor researching"
TO_RESEARCH_STATUS = "to research"


def _normalize_status(value: Any) -> str:
    """Normalize a status value for case-insensitive comparisons."""
    if not isinstance(value, str):
        return ""
    return " ".join(value.strip().lower().split())


def ensure_prefix(title: str, prefix: str = RESEARCH_PREFIX) -> str:
    """Prefix a title unless the prefix is already present."""
    normalized_title = title.strip()
    if normalized_title.lower().startswith(prefix.lower()):
        return normalized_title
    return f"{prefix} - {normalized_title}"


def update_issue_title_on_status_change(
    event_payload: Dict[str, Any],
) -> Optional[Dict[str, str]]:
    """
    Return a title update instruction when the issue moved to 'to research'.

    Expected event shape:
    {
      "triggerContext": {
        "trigger": "status_changed",
        "newStatus": "to research",
        "title": "Some issue title",
        "id": "POI-1234"
      }
    }
    """
    trigger_context = event_payload.get("triggerContext")
    if not isinstance(trigger_context, dict):
        return None

    if trigger_context.get("trigger") != "status_changed":
        return None

    new_status = _normalize_status(trigger_context.get("newStatus"))
    if new_status != TO_RESEARCH_STATUS:
        return None

    issue_id = trigger_context.get("id")
    title = trigger_context.get("title")
    if not isinstance(issue_id, str) or not issue_id.strip():
        return None
    if not isinstance(title, str) or not title.strip():
        return None

    new_title = ensure_prefix(title)
    if new_title == title:
        return None

    return {
        "issueId": issue_id,
        "oldTitle": title,
        "newTitle": new_title,
    }

