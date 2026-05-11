"""Build Linear issue title updates for research status changes."""

from collections.abc import Mapping
import re


TITLE_PREFIX = "Cursor researching"


def build_issue_title_update(event):
    """Return a title update action when an issue is moved to To Research.

    The automation layer can pass either the full trigger payload or the nested
    issue/trigger context. This function keeps the side effect at the boundary
    by returning the update that should be applied.
    """
    payload = _flatten_payload(event)
    if not payload:
        return None

    if not _is_status_changed_event(payload):
        return None

    if _normalize_status(_status_value(payload)) != "to research":
        return None

    issue_id = _first_text(payload, ("id", "issueId", "issue_id", "identifier"))
    title = _first_text(payload, ("title", "name"))
    if not issue_id or not title:
        return None

    stripped_title = title.strip()
    if not stripped_title or _has_title_prefix(stripped_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {stripped_title}",
    }


def _flatten_payload(value):
    if not isinstance(value, Mapping):
        return None

    payload = {}
    for key in ("data", "issue", "triggerContext"):
        nested = value.get(key)
        if isinstance(nested, Mapping):
            nested_payload = _flatten_payload(nested) or {}
            payload.update(nested_payload)
            payload.update(_public_items(nested))

    payload.update(_public_items(value))
    return payload


def _public_items(mapping):
    return {
        key: value
        for key, value in mapping.items()
        if key not in {"data", "issue", "triggerContext"}
    }


def _is_status_changed_event(payload):
    trigger_text = _first_text(payload, ("trigger", "webhookType", "action", "type"))
    normalized_trigger = _normalize_status(trigger_text)

    if normalized_trigger in {
        "status changed",
        "status change",
        "statuschanged",
        "issue status changed",
    }:
        return True

    if normalized_trigger in {"issue updated", "issue update", "updated", "update"}:
        updated_fields = payload.get("updatedFields") or payload.get("updated_fields")
        return _contains_status_field(updated_fields)

    return False


def _contains_status_field(value):
    if isinstance(value, str):
        return _normalize_status(value) in {"status", "state", "status name", "state name"}

    if isinstance(value, Mapping):
        return any(_contains_status_field(item) for item in value.keys())

    try:
        iterator = iter(value)
    except TypeError:
        return False

    return any(_contains_status_field(item) for item in iterator)


def _status_value(payload):
    status = _first_text(payload, ("newStatus", "new_status", "status"))
    if status:
        return status

    state = payload.get("state")
    if isinstance(state, Mapping):
        return _first_text(state, ("name", "title"))

    return None


def _first_text(mapping, keys):
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _normalize_status(value):
    if not isinstance(value, str):
        return ""

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    normalized = re.sub(r"[^A-Za-z0-9]+", " ", spaced).strip().lower()
    return re.sub(r"\s+", " ", normalized)


def _has_title_prefix(title):
    return title.casefold().startswith(TITLE_PREFIX.casefold())
