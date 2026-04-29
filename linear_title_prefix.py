"""Helpers for building Linear issue title updates from automation events."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_CHANGED_TRIGGER = "status changed"
UPDATE_ACTION = "update_issue_title"


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update action when an issue moves to the research status."""
    if not isinstance(event, Mapping):
        return None

    issue = _issue_context(event)
    trigger = _first_text(event, "trigger", "action") or _first_text(
        issue, "trigger", "action"
    )
    if _normalize(trigger) != STATUS_CHANGED_TRIGGER:
        return None

    if _normalize(_status(issue)) != TARGET_STATUS:
        return None

    issue_id = _first_text(issue, "id", "issueId", "identifier") or _first_text(
        event, "issueId", "id", "identifier"
    )
    title = _first_text(issue, "title") or _first_text(event, "title")
    if not issue_id or not title:
        return None

    if title.casefold().startswith(TITLE_PREFIX.casefold()):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _issue_context(event: Mapping[str, Any]) -> Mapping[str, Any]:
    for key in ("triggerContext", "data", "issue"):
        value = event.get(key)
        if isinstance(value, Mapping):
            return value
    return event


def _status(context: Mapping[str, Any]) -> Any:
    status = context.get("newStatus", context.get("status", context.get("state")))
    if isinstance(status, Mapping):
        return status.get("name") or status.get("title")
    return status


def _first_text(context: Mapping[str, Any], *keys: str) -> str:
    for key in keys:
        value = context.get(key)
        if isinstance(value, str):
            text = value.strip()
            if text:
                return text
    return ""


def _normalize(value: Any) -> str:
    if value is None:
        return ""

    text = str(value).strip()
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[\s_-]+", " ", text)
    return text.casefold().strip()
