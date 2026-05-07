"""Build Linear issue title updates for Cursor research automation."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when an issue moves to "to research"."""

    if not isinstance(event, Mapping):
        return None

    payload = _issue_payload(event)
    if not payload:
        return None

    if not _is_status_change(event, payload):
        return None

    if _normalize_status(_first_value(payload, "newStatus", "new_status", "status", "state.name")) != TARGET_STATUS:
        return None

    issue_id = _clean_text(_first_value(payload, "id", "issueId", "issue_id", "identifier"))
    title = _clean_text(_first_value(payload, "title"))
    if not issue_id or not title or _has_research_prefix(title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _issue_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for section in (event.get("data"), event.get("issue")):
        if isinstance(section, Mapping):
            issue = section.get("issue") if isinstance(section.get("issue"), Mapping) else section
            payload.update(issue)

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        payload.update(trigger_context)

    payload.update(event)
    return payload


def _is_status_change(event: Mapping[str, Any], payload: Mapping[str, Any]) -> bool:
    for source in (event, payload):
        for key in ("trigger", "action", "type", "webhookType"):
            value = source.get(key)
            if isinstance(value, str) and _normalize_token(value) == "statuschanged":
                return True
    return False


def _first_value(payload: Mapping[str, Any], *paths: str) -> Any:
    for path in paths:
        value = _get_path(payload, path)
        if value is not None:
            return value
    return None


def _get_path(payload: Mapping[str, Any], path: str) -> Any:
    value: Any = payload
    for part in path.split("."):
        if not isinstance(value, Mapping) or part not in value:
            return None
        value = value[part]
    return value


def _clean_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def _normalize_status(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    words = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value.strip())
    words = re.sub(r"[^A-Za-z0-9]+", " ", words).strip().lower()
    return words or None


def _normalize_token(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "", value).lower()


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())
