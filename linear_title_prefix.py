"""Build Linear issue title updates for research status transitions."""

from collections.abc import Mapping
import re


ACTION_UPDATE_ISSUE_TITLE = "update_issue_title"
RESEARCH_STATUS = "to research"
TITLE_PREFIX = "Cursor researching"


def build_issue_title_update(event):
    """Return an issue-title update action when a Linear issue enters research."""
    if not isinstance(event, Mapping):
        return None

    context = _trigger_context(event)
    if _normalize_token(context.get("trigger")) != "status changed":
        return None

    new_status = context.get("newStatus", context.get("status"))
    if _normalize_token(new_status) != RESEARCH_STATUS:
        return None

    issue_id = _first_text(context, "id", "issueId")
    title = _first_text(context, "title")
    if not issue_id or not title:
        return None

    normalized_title = title.strip()
    if not normalized_title or _has_research_prefix(normalized_title):
        return None

    return {
        "action": ACTION_UPDATE_ISSUE_TITLE,
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {normalized_title}",
    }


def _trigger_context(event):
    context = event.get("triggerContext")
    return context if isinstance(context, Mapping) else event


def _normalize_token(value):
    if not isinstance(value, str):
        return ""
    return re.sub(r"[\s_-]+", " ", value.strip().lower())


def _first_text(mapping, *keys):
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, str):
            stripped = value.strip()
            if stripped:
                return stripped
    return ""


def _has_research_prefix(title):
    return title.lower().startswith(TITLE_PREFIX.lower())
