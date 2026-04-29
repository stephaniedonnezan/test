"""Helpers for prefixing Linear issue titles when research starts."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Build a Linear issue title update for status changes to "to research".

    The automation webhook may provide issue fields at the top level or under
    common Linear-style nesting keys, so this helper accepts both shapes while
    returning a narrow update command for the caller to execute.
    """
    if not isinstance(event, Mapping):
        return None

    payload = _payload(event)
    if _normalize_token(_value(event, payload, "trigger", "webhookType")) != "status changed":
        return None

    status = _status_value(event, payload)
    if _normalize_token(status) != TARGET_STATUS:
        return None

    issue_id = _text(_value(event, payload, "id", "issueId", "identifier"))
    title = _text(_value(event, payload, "title"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_prefix(title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _payload(event: Mapping[str, Any]) -> Mapping[str, Any]:
    for key in ("data", "issue", "triggerContext"):
        value = event.get(key)
        if isinstance(value, Mapping):
            return value
    return event


def _value(
    event: Mapping[str, Any],
    payload: Mapping[str, Any],
    *keys: str,
) -> Any:
    for source in (payload, event):
        for key in keys:
            value = source.get(key)
            if value is not None:
                return value
    return None


def _status_value(event: Mapping[str, Any], payload: Mapping[str, Any]) -> Any:
    value = _value(event, payload, "newStatus", "status")
    if value is not None:
        return value

    for source in (payload, event):
        state = source.get("state")
        if isinstance(state, Mapping) and state.get("name") is not None:
            return state["name"]
    return None


def _text(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _normalize_token(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return re.sub(r"[-_\s]+", " ", value.strip()).lower()


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())
