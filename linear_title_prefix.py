"""Build Linear issue title updates for research-status automations."""

from collections.abc import Mapping
import re


RESEARCH_PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"
STATUS_CHANGED_TRIGGER = "status changed"


def build_issue_title_update(event):
    """Return a Linear title update payload when an issue moves to research."""
    if not isinstance(event, Mapping):
        return None

    context = _trigger_context(event)
    if _normalize(context.get("trigger")) != STATUS_CHANGED_TRIGGER:
        return None

    if _normalize(context.get("newStatus") or context.get("status")) != RESEARCH_STATUS:
        return None

    issue_id = _string_value(context.get("id") or context.get("issueId"))
    title = _string_value(context.get("title"))
    if not issue_id or not title:
        return None

    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{RESEARCH_PREFIX}: {title}",
    }


def _trigger_context(event):
    context = event.get("triggerContext")
    if isinstance(context, Mapping):
        return context
    return event


def _string_value(value):
    if not isinstance(value, str):
        return None

    stripped = value.strip()
    return stripped or None


def _normalize(value):
    if not isinstance(value, str):
        return ""

    normalized = re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()
    return re.sub(r"\s+", " ", normalized)


def _has_research_prefix(title):
    return title.lower().startswith(RESEARCH_PREFIX.lower())
