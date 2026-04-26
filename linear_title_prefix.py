"""Helpers for Linear issue title updates triggered by status changes."""

from __future__ import annotations

import re
from typing import Any, Mapping


ACTION_UPDATE_ISSUE_TITLE = "update_issue_title"
RESEARCH_STATUS = "to research"
TITLE_PREFIX = "Cursor researching"
CURSOR_RESEARCHING_PREFIX = TITLE_PREFIX


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title-update action when a Linear issue moves to To Research.

    The automation payload is expected to contain Linear's webhook fields under
    ``triggerContext``. Flat dictionaries are also accepted to keep the helper
    easy to test and reuse.
    """

    payload = _event_payload(event)
    if _normalize_token(payload.get("trigger")) != "status changed":
        return None

    new_status = payload.get("newStatus", payload.get("status"))
    if _normalize_token(new_status) != RESEARCH_STATUS:
        return None

    issue_id = payload.get("id") or payload.get("issueId")
    title = payload.get("title")
    if not issue_id or not isinstance(title, str) or not title.strip():
        return None
    if not needs_researching_prefix(title):
        return None

    return {
        "action": ACTION_UPDATE_ISSUE_TITLE,
        "issueId": str(issue_id),
        "title": prefixed_title(title),
    }


def add_researching_prefix(title: str) -> str:
    """Prefix ``title`` with the Cursor researching marker once."""

    return prefixed_title(title)


def prefixed_title(title: str) -> str:
    """Return ``title`` with the Cursor researching marker prepended."""

    stripped_title = title.strip()
    if not needs_researching_prefix(stripped_title):
        return stripped_title
    return f"{TITLE_PREFIX}: {stripped_title}"


def needs_researching_prefix(title: Any) -> bool:
    """Return whether ``title`` needs the Cursor researching marker."""

    return isinstance(title, str) and bool(title.strip()) and not _has_researching_prefix(
        title
    )


def _event_payload(event: Mapping[str, Any]) -> Mapping[str, Any]:
    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        return trigger_context
    return event


def _normalize_token(value: Any) -> str:
    if value is None:
        return ""
    normalized = re.sub(r"[^a-z0-9]+", " ", str(value).lower())
    return " ".join(normalized.split())


def normalized_value(value: Any) -> str:
    """Normalize Linear webhook values for forgiving comparisons."""

    return _normalize_token(value)


def _has_researching_prefix(title: str) -> bool:
    normalized_title = _normalize_token(title)
    normalized_prefix = _normalize_token(TITLE_PREFIX)
    return normalized_title == normalized_prefix or normalized_title.startswith(
        f"{normalized_prefix} "
    )
