"""Build title update actions for Linear issue status-change automations."""

from collections.abc import Mapping
import re


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_CHANGED_TRIGGER = "status_changed"


def build_issue_title_update(event):
    """Return an issue-title update action when an issue moves to research.

    The automation trigger payload may be provided either as the full Cursor
    automation event with a nested ``triggerContext`` object or directly as the
    trigger context itself.
    """
    if not isinstance(event, Mapping):
        return None

    context = event.get("triggerContext")
    if not isinstance(context, Mapping):
        context = event

    if _normalize_token(context.get("trigger")) != _normalize_token(STATUS_CHANGED_TRIGGER):
        return None

    new_status = context.get("newStatus", context.get("status"))
    if _normalize_status(new_status) != TARGET_STATUS:
        return None

    issue_id = _first_text(context, "id", "issueId")
    title = _first_text(context, "title")
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_researching_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _first_text(payload, *keys):
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _normalize_token(value):
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def _normalize_status(value):
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^a-z0-9]+", " ", value.strip().lower()).strip()


def _has_researching_prefix(title):
    return title.lower().startswith(TITLE_PREFIX.lower())
