"""Build Linear issue title updates for research status transitions."""

from collections.abc import Mapping
import re


RESEARCH_STATUS = "to research"
TITLE_PREFIX = "Cursor researching"


def build_issue_title_update(event):
    """Return an issue-title update action when a Linear issue moves to research.

    The automation payload may expose issue fields either at the top level or
    under ``triggerContext``. Non-status-change events and non-research statuses
    are ignored by returning ``None``.
    """
    if not isinstance(event, Mapping):
        return None

    context = _context_for(event)
    if _normalize_token(context.get("trigger")) != "status changed":
        return None

    status = context.get("newStatus", context.get("status"))
    if _normalize_token(status) != RESEARCH_STATUS:
        return None

    issue_id = _first_string(context, "id", "issueId")
    title = _first_string(context, "title")
    if not issue_id or not title:
        return None

    title = title.strip()
    if not title or _already_prefixed(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _context_for(event):
    context = event.get("triggerContext")
    if isinstance(context, Mapping):
        merged = dict(event)
        merged.update(context)
        return merged
    return event


def _normalize_token(value):
    if not isinstance(value, str):
        return ""
    normalized = re.sub(r"[_-]+", " ", value.strip().lower())
    return re.sub(r"\s+", " ", normalized)


def _first_string(mapping, *keys):
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, str):
            return value
    return ""


def _already_prefixed(title):
    return title.lower().startswith(TITLE_PREFIX.lower())
