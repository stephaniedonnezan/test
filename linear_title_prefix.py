"""Build Linear issue title updates for Cursor research automation."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


CURSOR_RESEARCHING_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update when an issue moves to To Research."""
    if not isinstance(event, Mapping):
        return None

    payload = _flatten_event(event)
    if not _is_status_change_event(payload):
        return None

    status = _first_text(payload, "newStatus", "new_status", "status")
    if status is None:
        status = _nested_text(payload.get("state"), "name")

    if _normalize_value(status) != _normalize_value(TARGET_STATUS):
        return None

    issue_id = _first_text(payload, "id", "issueId", "issue_id", "identifier")
    title = _first_text(payload, "title")
    if not issue_id or not title:
        return None

    stripped_title = title.strip()
    if _has_cursor_researching_prefix(stripped_title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id,
        "title": f"{CURSOR_RESEARCHING_PREFIX}: {stripped_title}",
    }


def _flatten_event(event: Mapping[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}

    for key in ("issue", "data", "triggerContext"):
        value = event.get(key)
        if isinstance(value, Mapping):
            payload.update(_flatten_event(value))

    payload.update(event)
    return payload


def _is_status_change_event(payload: Mapping[str, Any]) -> bool:
    trigger = _first_text(payload, "trigger", "webhookType", "action", "type")
    if trigger and _normalize_value(trigger) in {
        "status changed",
        "status change",
        "statuschanged",
        "state changed",
        "state change",
        "statechanged",
    }:
        return True

    updated_fields = payload.get("updatedFields") or payload.get("updated_fields")
    if _contains_status_field(updated_fields):
        return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_value(value) in {"status", "state"}

    if isinstance(value, Mapping):
        return any(_contains_status_field(item) for item in value.keys())

    if isinstance(value, (list, tuple, set)):
        return any(_contains_status_field(item) for item in value)

    return False


def _first_text(payload: Mapping[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str):
            text = value.strip()
            if text:
                return text
    return None


def _nested_text(value: Any, key: str) -> str | None:
    if not isinstance(value, Mapping):
        return None

    nested_value = value.get(key)
    if not isinstance(nested_value, str):
        return None

    text = nested_value.strip()
    return text or None


def _normalize_value(value: str | None) -> str:
    if not value:
        return ""

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return re.sub(r"[^a-z0-9]+", " ", spaced.lower()).strip()


def _has_cursor_researching_prefix(title: str) -> bool:
    return title.lower().startswith(CURSOR_RESEARCHING_PREFIX.lower())
