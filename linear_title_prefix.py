"""Build title updates for Linear issues entering research."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_CHANGED = "status changed"
UPDATE_ACTION = "update_issue_title"


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update when an issue moves to "to research".

    Cursor automation payloads may include trigger fields at the top level,
    under ``triggerContext``, or alongside nested Linear ``data``/``issue``
    objects. This function accepts those shapes and returns a serializable
    update operation for the caller to apply.
    """

    if not isinstance(event, Mapping):
        return None

    payload = _flatten_payload(event)
    if not _is_status_changed(payload):
        return None

    status = _first_value(payload, ("newStatus", "new_status", "status"))
    if _normalize(status) != TARGET_STATUS:
        return None

    issue_id = _string_value(_first_value(payload, ("id", "issueId", "issue_id", "identifier")))
    title = _string_value(_first_value(payload, ("title", "name")))
    if not issue_id or not title:
        return None

    if _has_prefix(title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _flatten_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}

    for key in ("data", "issue", "triggerContext"):
        value = event.get(key)
        if isinstance(value, Mapping):
            payload.update(_flatten_payload(value))

    state = event.get("state")
    if isinstance(state, Mapping) and "status" not in payload:
        payload["status"] = state.get("name")

    payload.update(event)
    return payload


def _is_status_changed(payload: Mapping[str, Any]) -> bool:
    trigger = _first_value(payload, ("trigger", "webhookType", "action", "type"))
    return _normalize(trigger) == STATUS_CHANGED


def _first_value(payload: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = payload.get(key)
        if value is not None:
            return value
    return None


def _string_value(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    stripped = value.strip()
    return stripped or None


def _normalize(value: Any) -> str | None:
    text = _string_value(value)
    if text is None:
        return None

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    normalized = re.sub(r"[^a-zA-Z0-9]+", " ", spaced).strip().casefold()
    return re.sub(r"\s+", " ", normalized)


def _has_prefix(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())
