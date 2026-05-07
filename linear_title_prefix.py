"""Build Linear issue title updates for research-status automations."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_CHANGE_TRIGGER = "status changed"

_NESTED_EVENT_KEYS = ("triggerContext", "data", "payload", "issue")
_TRIGGER_KEYS = ("trigger", "action", "type", "webhookType", "webhook_type")
_STATUS_KEYS = ("newStatus", "new_status", "newState", "new_state", "status")
_ISSUE_ID_KEYS = ("id", "issueId", "issue_id", "identifier")
_TITLE_KEYS = ("title", "name")


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title-update action when a Linear issue moves to research.

    The automation trigger payload has varied slightly across runs, so this
    accepts both the flat Cursor trigger shape and common nested Linear webhook
    shapes. Invalid or non-matching payloads are intentionally ignored.
    """

    payload = _flatten_event(event)
    if not payload:
        return None

    if _normalize_token(_first_string(payload, _TRIGGER_KEYS)) != STATUS_CHANGE_TRIGGER:
        return None

    if _normalize_token(_status_value(payload)) != TARGET_STATUS:
        return None

    issue_id = _first_string(payload, _ISSUE_ID_KEYS)
    title = _first_string(payload, _TITLE_KEYS)
    if issue_id is None or title is None:
        return None

    issue_id = issue_id.strip()
    title = title.strip()
    if not issue_id or not title or _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _flatten_event(event: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(event, Mapping):
        return {}

    flattened: dict[str, Any] = {}
    for key in _NESTED_EVENT_KEYS:
        nested = event.get(key)
        if isinstance(nested, Mapping):
            flattened.update(_flatten_event(nested))

    for key, value in event.items():
        if key not in _NESTED_EVENT_KEYS:
            flattened[key] = value

    return flattened


def _status_value(payload: Mapping[str, Any]) -> Any:
    status = _first_value(payload, _STATUS_KEYS)
    if status is not None:
        return status

    state = payload.get("state")
    if isinstance(state, Mapping):
        return _first_value(state, ("name", "title"))

    return None


def _first_string(payload: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    value = _first_value(payload, keys)
    if value is None:
        return None

    return str(value)


def _first_value(payload: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = payload.get(key)
        if value is not None:
            return value

    return None


def _normalize_token(value: Any) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[\W_]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().casefold()


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(TITLE_PREFIX.casefold())
