"""Helpers for adding a Cursor research prefix to Linear issue titles."""

from collections.abc import Mapping
import re


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
TRIGGER_STATUS_CHANGED = "status changed"


def build_issue_title_update(event):
    """Return a title update action when a Linear issue moves to research."""
    if not isinstance(event, Mapping):
        return None

    payload = _payload(event)
    if _trigger(event, payload) != TRIGGER_STATUS_CHANGED:
        return None

    status = _status(payload)
    if _normalize(status) != TARGET_STATUS:
        return None

    issue_id = payload.get("id") or payload.get("issueId") or event.get("issueId")
    title = payload.get("title") or event.get("title")
    if not issue_id or not isinstance(title, str):
        return None

    stripped_title = title.strip()
    if not stripped_title or stripped_title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {stripped_title}",
    }


def _payload(event):
    data = event.get("data")
    if isinstance(data, Mapping):
        return data
    issue = event.get("issue")
    if isinstance(issue, Mapping):
        return issue
    return event


def _status(payload):
    status = payload.get("newStatus", payload.get("status", payload.get("state")))
    if isinstance(status, Mapping):
        return status.get("name") or status.get("title")
    return status


def _trigger(event, payload):
    trigger = event.get("trigger") or payload.get("trigger") or event.get("action")
    if trigger == "statusChanged":
        return TRIGGER_STATUS_CHANGED
    return _normalize(trigger)


def _normalize(value):
    if value is None:
        return ""
    spaced = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", str(value).strip())
    return re.sub(r"[\s_-]+", " ", spaced.lower())
