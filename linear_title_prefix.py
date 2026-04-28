"""Build Linear issue title updates for research status changes."""

from collections.abc import Mapping
import re


PREFIX = "Cursor researching"
PREFIXED_TITLE = f"{PREFIX}: "
TARGET_STATUS = "to research"
STATUS_CHANGED_TRIGGER = "status changed"


def build_issue_title_update(event):
    """Return a Linear title update action when an issue moves to research."""
    if not isinstance(event, Mapping):
        return None

    context = _trigger_context(event)
    if _normalize(context.get("trigger")) != STATUS_CHANGED_TRIGGER:
        return None

    status = context.get("newStatus", context.get("status"))
    if _normalize(status) != TARGET_STATUS:
        return None

    issue_id = context.get("id", context.get("issueId"))
    title = context.get("title")
    if not issue_id or not isinstance(title, str):
        return None

    clean_title = title.strip()
    if not clean_title or _has_prefix(clean_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIXED_TITLE}{clean_title}",
    }


def _trigger_context(event):
    context = event.get("triggerContext")
    if isinstance(context, Mapping):
        return context
    return event


def _normalize(value):
    if not isinstance(value, str):
        return None
    normalized = re.sub(r"[_-]+", " ", value.strip().casefold())
    return re.sub(r"\s+", " ", normalized)


def _has_prefix(title):
    return title.casefold().startswith(PREFIX.casefold())
