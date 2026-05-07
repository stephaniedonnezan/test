"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update when an issue moves to the research status."""
    if not isinstance(event, Mapping):
        return None

    payload = _issue_payload(event)
    context = _context_payload(event)

    if not _is_status_changed(event, context):
        return None

    new_status = _first_text(
        event,
        context,
        payload,
        keys=("newStatus", "new_status", "status"),
    ) or _nested_text(payload, ("state", "name"))

    if _normalize_text(new_status) != _normalize_text(TARGET_STATUS):
        return None

    issue_id = _first_text(
        event,
        context,
        payload,
        keys=("issueId", "issue_id", "id", "identifier"),
    )
    title = _first_text(event, context, payload, keys=("title",))

    if not issue_id or not title:
        return None

    stripped_title = title.strip()
    if _has_prefix(stripped_title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {stripped_title}",
    }


def _issue_payload(event: Mapping[str, Any]) -> Mapping[str, Any]:
    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            return issue
        return data

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        return issue

    return event


def _context_payload(event: Mapping[str, Any]) -> Mapping[str, Any]:
    context = event.get("triggerContext")
    if isinstance(context, Mapping):
        return context
    return {}


def _is_status_changed(
    event: Mapping[str, Any], context: Mapping[str, Any]
) -> bool:
    trigger = _first_text(
        event,
        context,
        keys=("trigger", "webhookType", "action", "type"),
    )
    return _normalize_text(trigger) == "status changed"


def _first_text(
    *payloads: Mapping[str, Any],
    keys: tuple[str, ...],
) -> str | None:
    for payload in payloads:
        for key in keys:
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _nested_text(payload: Mapping[str, Any], path: tuple[str, ...]) -> str | None:
    current: Any = payload
    for key in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)

    if isinstance(current, str) and current.strip():
        return current.strip()
    return None


def _has_prefix(title: str) -> bool:
    return title.casefold().startswith(TITLE_PREFIX.casefold())


def _normalize_text(value: str | None) -> str:
    if value is None:
        return ""

    spaced = re.sub(r"(?<!^)(?=[A-Z])", " ", value.strip())
    normalized = re.sub(r"[\W_]+", " ", spaced, flags=re.ASCII)
    return " ".join(normalized.casefold().split())
