"""Build Linear issue title updates for research status changes."""

from collections.abc import Mapping
import re


PREFIX = "Cursor researching"
PREFIXED_TITLE = f"{PREFIX}: {{title}}"
TARGET_STATUS = "to research"
TARGET_TRIGGER = "status_changed"


def build_issue_title_update(event):
    """Return an issue title update action for Linear research status changes.

    The automation payload may be passed either as the full webhook envelope
    (`{"triggerContext": ...}`) or directly as the trigger context. Non-mapping
    payloads and irrelevant status changes are ignored.
    """
    if not isinstance(event, Mapping):
        return None

    context = event.get("triggerContext")
    if not isinstance(context, Mapping):
        context = event

    if _normalize_token(context.get("trigger")) != _normalize_token(TARGET_TRIGGER):
        return None

    status = context.get("newStatus", context.get("status"))
    if _normalize_status(status) != TARGET_STATUS:
        return None

    issue_id = context.get("id", context.get("issueId"))
    title = context.get("title")
    if not issue_id or not isinstance(title, str):
        return None

    title = title.strip()
    if not title or _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": PREFIXED_TITLE.format(title=title),
    }


def _normalize_status(value):
    if not isinstance(value, str):
        return ""
    return re.sub(r"[\s_-]+", " ", value.strip().lower())


def _normalize_token(value):
    if not isinstance(value, str):
        return ""
    return re.sub(r"[\s-]+", "_", value.strip().lower())


def _has_research_prefix(title):
    return title.lower().startswith(PREFIX.lower())
