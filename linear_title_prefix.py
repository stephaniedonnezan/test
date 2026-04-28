"""Build Linear issue title updates for research-status transitions."""

from collections.abc import Mapping
import re


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_CHANGED_TRIGGER = "status_changed"


def build_issue_title_update(event):
    """Return an issue-title update payload for matching Linear webhook events.

    The automation receives Linear trigger details either at the top level or
    under ``triggerContext``. Only status-change events moving an issue to
    "to research" should add the title prefix.
    """
    if not isinstance(event, Mapping):
        return None

    context = _event_context(event)
    if _normalize_token(context.get("trigger")) != STATUS_CHANGED_TRIGGER:
        return None

    status = context.get("newStatus", context.get("status"))
    if _normalize_status(status) != TARGET_STATUS:
        return None

    title = _clean_text(context.get("title"))
    if not title or _has_researching_prefix(title):
        return None

    issue_id = _clean_text(context.get("id", context.get("issueId")))
    if not issue_id:
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _event_context(event):
    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        return trigger_context
    return event


def _clean_text(value):
    if not isinstance(value, str):
        return None
    return value.strip()


def _normalize_status(value):
    text = _clean_text(value)
    if text is None:
        return None
    return re.sub(r"[\s_-]+", " ", text).strip().casefold()


def _normalize_token(value):
    text = _clean_text(value)
    if text is None:
        return None
    return re.sub(r"[\s-]+", "_", text).strip("_").casefold()


def _has_researching_prefix(title):
    return title.casefold().startswith(TITLE_PREFIX.casefold())
