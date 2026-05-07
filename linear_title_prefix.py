"""Build title update actions for Linear issues entering research."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to research.

    The automation payloads can be flat or nested under ``triggerContext`` /
    ``data`` / ``issue`` depending on where they originate, so this function
    normalizes the common shapes before checking the status transition.
    """

    if not isinstance(event, Mapping):
        return None

    payload = _flatten_event(event)
    if not _is_status_changed_event(payload):
        return None

    status = _first_string(
        payload,
        "newStatus",
        "new_status",
        "status",
        "statusName",
        "stateName",
    )
    if status is None:
        state = payload.get("state")
        if isinstance(state, Mapping):
            status = _first_string(state, "name")

    if _normalize_status(status) != TARGET_STATUS:
        return None

    issue_id = _first_string(payload, "id", "issueId", "issue_id", "identifier")
    title = _first_string(payload, "title")
    if issue_id is None or title is None:
        return None

    title = title.strip()
    if not title or _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _flatten_event(event: Mapping[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        payload.update(trigger_context)

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            payload.update(issue)
        payload.update(data)

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        payload.update(issue)

    payload.update(event)
    return payload


def _is_status_changed_event(payload: Mapping[str, Any]) -> bool:
    trigger = _first_string(payload, "trigger", "webhookType", "action", "type")
    if trigger is None:
        return False

    normalized_trigger = _normalize_token(trigger)
    if normalized_trigger in {"statuschanged", "statuschange", "statusupdated"}:
        return True

    if normalized_trigger in {"issueupdated", "updated"}:
        updated_fields = payload.get("updatedFields")
        if isinstance(updated_fields, (list, tuple, set)):
            return any(_normalize_token(field) in {"status", "state"} for field in updated_fields)

    return False


def _first_string(payload: Mapping[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str):
            return value
    return None


def _normalize_status(value: str | None) -> str | None:
    if value is None:
        return None
    words = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    words = re.sub(r"[^a-zA-Z0-9]+", " ", words).strip().lower()
    return re.sub(r"\s+", " ", words)


def _normalize_token(value: Any) -> str:
    words = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", str(value))
    return re.sub(r"[^a-zA-Z0-9]+", "", words).lower()


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())
