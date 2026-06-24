"""Build title updates for Linear issues entering research."""

from collections.abc import Mapping
import re


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"


def build_issue_title_update(event):
    """Return a Linear issue title update for research status changes.

    The automation runtime is expected to perform the actual Linear mutation
    from the returned instruction. Non-matching or incomplete payloads are
    ignored by returning None.
    """
    if not isinstance(event, Mapping):
        return None

    payload = _flatten_event(event)
    status = _first_present(payload, ("newStatus", "new_status", "status", "state"))
    if not _is_status_change(payload):
        return None

    if _normalize_value(status) != TARGET_STATUS:
        return None

    issue_id = _extract_issue_id(payload)
    title = _extract_title(payload)
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_prefix(title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _flatten_event(event):
    """Merge common Linear webhook nesting levels into one payload."""
    payload = {}

    for key in ("triggerContext", "data", "issue"):
        value = event.get(key)
        if isinstance(value, Mapping):
            payload.update(_flatten_event(value))

    payload.update(event)
    return payload


def _is_status_change(payload):
    candidates = (
        payload.get("trigger"),
        payload.get("webhookType"),
        payload.get("action"),
        payload.get("type"),
    )
    return any(_normalize_value(candidate) == "status changed" for candidate in candidates)


def _extract_issue_id(payload):
    value = _first_present(payload, ("id", "issueId", "issue_id", "identifier"))
    if value is None:
        return None
    return str(value).strip() or None


def _extract_title(payload):
    value = payload.get("title")
    if value is None:
        return None
    return str(value).strip() or None


def _first_present(payload, keys):
    for key in keys:
        value = payload.get(key)
        if value is None:
            continue
        if isinstance(value, Mapping):
            name = value.get("name")
            if name is not None:
                return name
            continue
        return value
    return None


def _has_prefix(title):
    return title.lower().startswith(PREFIX.lower())


def _normalize_value(value):
    if value is None:
        return ""

    words = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", str(value))
    words = re.sub(r"[^A-Za-z0-9]+", " ", words)
    return " ".join(words.lower().split())
