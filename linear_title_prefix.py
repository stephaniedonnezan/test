"""Helpers for Linear issue title updates triggered by status changes."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
PREFIXED_TITLE_FORMAT = f"{TITLE_PREFIX}: {{title}}"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Build a title update for Linear issues moved to "to research".

    The automation runtime may provide the Linear payload directly or wrapped in
    fields such as ``triggerContext`` or ``data``. This function normalizes those
    common shapes and returns a simple action object for the caller to execute.
    """

    if not isinstance(event, Mapping):
        return None

    payload = _extract_payload(event)
    if not _is_status_change_event(payload):
        return None

    status = _first_text(payload, ("newStatus", "new_status", "status"))
    if status is None:
        state = payload.get("state")
        if isinstance(state, Mapping):
            status = _first_text(state, ("name", "status"))

    if _normalize_text(status) != _normalize_text(TARGET_STATUS):
        return None

    issue_id = _first_text(payload, ("id", "issueId", "issue_id", "identifier"))
    title = _first_text(payload, ("title",))
    if issue_id is None or title is None:
        return None

    stripped_title = title.strip()
    if not stripped_title or _has_prefix(stripped_title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id,
        "title": PREFIXED_TITLE_FORMAT.format(title=stripped_title),
    }


def _extract_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}

    for key in ("triggerContext", "data", "issue"):
        value = event.get(key)
        if isinstance(value, Mapping):
            payload.update(_extract_payload(value))

    payload.update(event)
    return payload


def _is_status_change_event(payload: Mapping[str, Any]) -> bool:
    trigger = _first_text(payload, ("trigger", "action", "type"))
    if _normalize_text(trigger) == "status changed":
        return True

    webhook_type = _first_text(payload, ("webhookType", "webhook_type"))
    normalized_webhook_type = _normalize_text(webhook_type)
    return normalized_webhook_type in {"issue", "status changed"} and _has_status_value(payload)


def _has_status_value(payload: Mapping[str, Any]) -> bool:
    if _first_text(payload, ("newStatus", "new_status", "status")) is not None:
        return True

    state = payload.get("state")
    return isinstance(state, Mapping) and _first_text(state, ("name", "status")) is not None


def _first_text(mapping: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, str):
            return value
    return None


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None

    spaced = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", value)
    return re.sub(r"[\s_-]+", " ", spaced).strip().casefold()


def _has_prefix(title: str) -> bool:
    return title.casefold().startswith(TITLE_PREFIX.casefold())
