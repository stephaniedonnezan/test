"""Build title updates for Linear issues entering the research status."""

from collections.abc import Mapping
import re


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_CHANGE_EVENTS = {
    "status changed",
    "status change",
    "statuschanged",
    "status_changed",
    "state changed",
    "state change",
    "statechanged",
    "state_changed",
}
_ISSUE_UPDATE_EVENTS = {
    "issue updated",
    "updated issue",
    "issueupdated",
    "issue_updated",
}
_STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow state"}


def build_issue_title_update(event):
    """Return a Linear title update action when an issue moves to research.

    The function is intentionally side-effect free so automation runners can
    call it from a webhook handler and decide how to apply the returned action.
    """
    if not isinstance(event, Mapping):
        return None

    payload = _merged_payload(event)
    if not _is_status_change(payload):
        return None

    if _normalize_status(_new_status(payload)) != TARGET_STATUS:
        return None

    issue_id = _first_text(payload, "id", "issueId", "issue_id", "identifier")
    title = _first_text(payload, "title", "name")
    if not issue_id or not title:
        return None

    if title.lower().startswith(TITLE_PREFIX.lower()):
        new_title = title
    else:
        new_title = f"{TITLE_PREFIX}: {title}"

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": new_title,
    }


def _merged_payload(event):
    payload = {}

    def merge(value):
        if isinstance(value, Mapping):
            payload.update(value)

    merge(event)

    trigger_context = event.get("triggerContext")
    merge(trigger_context)

    data = event.get("data")
    merge(data)
    if isinstance(data, Mapping):
        merge(data.get("issue"))

    merge(event.get("issue"))
    return payload


def _is_status_change(payload):
    for field in ("trigger", "action", "type"):
        value = payload.get(field)
        if _normalized_event_name(value) in _STATUS_CHANGE_EVENTS:
            return True

    for field in ("trigger", "action", "type"):
        event_name = _normalized_event_name(payload.get(field))
        if event_name in _ISSUE_UPDATE_EVENTS:
            return _updated_fields_include_status(payload.get("updatedFields"))

    return False


def _updated_fields_include_status(updated_fields):
    if isinstance(updated_fields, str):
        updated_fields = [updated_fields]

    if not isinstance(updated_fields, list):
        return False

    for field in updated_fields:
        normalized = _normalize_status(field)
        compact = normalized.replace(" ", "")
        if normalized in _STATUS_FIELD_NAMES or compact in _STATUS_FIELD_NAMES:
            return True

    return False


def _new_status(payload):
    for key in ("newStatus", "new_status", "status"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value

    for key in ("state", "workflowState"):
        value = payload.get(key)
        if isinstance(value, Mapping):
            name = value.get("name")
            if isinstance(name, str) and name.strip():
                return name
        elif isinstance(value, str) and value.strip():
            return value

    return None


def _first_text(payload, *keys):
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str):
            text = value.strip()
            if text:
                return text
    return None


def _normalized_event_name(value):
    if not isinstance(value, str):
        return ""
    spaced = _space_camel_case(value)
    return re.sub(r"[\s_-]+", " ", spaced).strip().lower()


def _normalize_status(value):
    if not isinstance(value, str):
        return ""
    spaced = _space_camel_case(value)
    return re.sub(r"[\s_-]+", " ", spaced).strip().lower()


def _space_camel_case(value):
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
