"""Build Linear issue title updates for research status transitions."""

from collections.abc import Mapping
import re


CURSOR_RESEARCHING_PREFIX = "Cursor researching"
UPDATE_ISSUE_TITLE_ACTION = "update_issue_title"
RESEARCH_STATUS = "to research"
STATUS_CHANGED_TRIGGER = "status_changed"


def build_issue_title_update(event):
    """Return an issue title update action when an issue moves to research."""
    context = _trigger_context(event)
    if not context:
        return None

    if _normalize(context.get("trigger")) != _normalize(STATUS_CHANGED_TRIGGER):
        return None

    new_status = context.get("newStatus", context.get("status"))
    if _normalize(new_status) != _normalize(RESEARCH_STATUS):
        return None

    issue_id = _string_or_none(context.get("id")) or _string_or_none(context.get("issueId"))
    title = _string_or_none(context.get("title"))
    if not issue_id or not title:
        return None

    stripped_title = title.strip()
    if _has_cursor_researching_prefix(stripped_title):
        return None

    return {
        "action": UPDATE_ISSUE_TITLE_ACTION,
        "issueId": issue_id,
        "title": f"{CURSOR_RESEARCHING_PREFIX}: {stripped_title}",
    }


def _trigger_context(event):
    if not isinstance(event, Mapping):
        return None

    nested_context = event.get("triggerContext")
    if isinstance(nested_context, Mapping):
        return nested_context

    return event


def _normalize(value):
    if not isinstance(value, str):
        return ""

    return re.sub(r"[\W_]+", " ", value).strip().casefold()


def _string_or_none(value):
    if not isinstance(value, str):
        return None

    stripped_value = value.strip()
    return stripped_value or None


def _has_cursor_researching_prefix(title):
    prefix_pattern = rf"^{re.escape(CURSOR_RESEARCHING_PREFIX)}(?:\s*[:-])?(?:\s+|$)"
    return re.match(prefix_pattern, title, flags=re.IGNORECASE) is not None
