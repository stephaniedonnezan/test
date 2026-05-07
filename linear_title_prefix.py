"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to research.

    Cursor automation payloads can be flat or nested under ``triggerContext``.
    Linear webhook fields may also be nested under ``data`` or ``issue``. This
    helper returns a small action object that an integration layer can apply via
    the Linear API.
    """

    if not isinstance(event, Mapping):
        return None

    payload = _issue_payload(event)
    if not _is_status_changed(event, payload):
        return None

    if not _has_target_status(payload):
        return None

    issue_id = _first_present(payload, "id", "issueId", "issue_id", "identifier")
    title = _first_present(payload, "title", "name")
    if not isinstance(issue_id, str) or not issue_id.strip():
        return None
    if not isinstance(title, str) or not title.strip():
        return None

    clean_title = title.strip()
    if _has_research_prefix(clean_title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {clean_title}",
    }


def _issue_payload(event: Mapping[str, Any]) -> Mapping[str, Any]:
    context = event.get("triggerContext")
    if isinstance(context, Mapping):
        outer = {key: value for key, value in event.items() if key != "triggerContext"}
        return _issue_payload({**context, **outer})

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            return {**data, **issue, **event}
        return {**data, **event}

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        return {**issue, **event}

    return event


def _is_status_changed(event: Mapping[str, Any], payload: Mapping[str, Any]) -> bool:
    event_name = _first_present(event, "trigger", "webhookType", "action", "type")
    payload_event_name = _first_present(payload, "trigger", "webhookType", "action", "type")
    return (
        _normalize_event_name(event_name) == "statuschanged"
        or _normalize_event_name(payload_event_name) == "statuschanged"
    )


def _has_target_status(payload: Mapping[str, Any]) -> bool:
    status = _first_present(payload, "newStatus", "new_status", "status")
    if _normalize_status(status) == TARGET_STATUS:
        return True

    state = payload.get("state")
    return isinstance(state, Mapping) and _normalize_status(state.get("name")) == TARGET_STATUS


def _first_present(mapping: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        value = mapping.get(key)
        if value is not None:
            return value
    return None


def _normalize_status(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return _normalize_words(value)


def _normalize_event_name(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return _normalize_words(value).replace(" ", "")


def _normalize_words(value: str) -> str:
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    return re.sub(r"[^a-z0-9]+", " ", spaced.casefold()).strip()


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(TITLE_PREFIX.casefold())
