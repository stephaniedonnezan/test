"""Build title updates for Linear issue status-change webhooks."""

from collections.abc import Mapping
import re


TITLE_PREFIX = "Cursor researching"


def build_issue_title_update(event):
    """Return a title update action when a Linear issue moves to to research."""
    payload = _payload(event)
    if not payload or not _is_status_changed(payload):
        return None

    status = _first_text(
        payload,
        "newStatus",
        "new_status",
        "status",
        ("state", "name"),
    )
    if _normalize(status) != "to research":
        return None

    issue_id = _first_text(payload, "id", "issueId", "issue_id", ("issue", "id"))
    title = _first_text(payload, "title", ("issue", "title"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _payload(event):
    if not isinstance(event, Mapping):
        return None

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        return trigger_context

    data = event.get("data")
    if isinstance(data, Mapping):
        payload = dict(event)
        payload.update(data)
        return payload

    return event


def _is_status_changed(payload):
    trigger = _first_text(payload, "trigger", "webhookType", "action", "type")
    return _normalize(trigger) == "status changed"


def _first_text(payload, *paths):
    for path in paths:
        value = _get_path(payload, path if isinstance(path, tuple) else (path,))
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _get_path(payload, path):
    value = payload
    for key in path:
        if not isinstance(value, Mapping):
            return None
        value = value.get(key)
    return value


def _normalize(value):
    if not isinstance(value, str):
        return ""
    spaced = re.sub(r"(?<!^)(?=[A-Z])", " ", value)
    return re.sub(r"[\s_-]+", " ", spaced).strip().casefold()


def _has_prefix(title):
    return title.casefold().startswith(TITLE_PREFIX.casefold())
