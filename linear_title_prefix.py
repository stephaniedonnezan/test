"""Build title update actions for Linear issues moved to research."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


RESEARCH_TITLE_PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"
STATUS_CHANGED_TRIGGER = "status changed"


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title-update action when a Linear issue moves to research.

    The automation payloads used by Cursor can contain issue data either at the
    top level, under ``triggerContext``, or nested under ``data``/``issue``.
    """

    if not isinstance(event, Mapping):
        return None

    payload = _flatten_event(event)
    if not _is_status_changed(payload):
        return None

    if _normalize_text(_first_text(payload, "newStatus", "new_status", "status", "state.name")) != RESEARCH_STATUS:
        return None

    issue_id = _first_text(payload, "id", "issueId", "issue_id", "identifier")
    title = _first_text(payload, "title")
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{RESEARCH_TITLE_PREFIX}: {title}",
    }


def _flatten_event(event: Mapping[str, Any]) -> dict[str, Any]:
    flattened: dict[str, Any] = {}

    def visit(value: Any) -> None:
        if not isinstance(value, Mapping):
            return

        for key in ("triggerContext", "data", "issue"):
            nested = value.get(key)
            if isinstance(nested, Mapping):
                visit(nested)

        for key, item in value.items():
            if key in {"triggerContext", "data", "issue"}:
                continue
            flattened[key] = item

    visit(event)
    return flattened


def _is_status_changed(payload: Mapping[str, Any]) -> bool:
    return any(
        _normalize_text(_first_text(payload, key)) == STATUS_CHANGED_TRIGGER
        for key in ("trigger", "webhookType", "action", "type")
    )


def _first_text(payload: Mapping[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = _get_nested(payload, key)
        if value is None:
            continue

        if isinstance(value, Mapping):
            value = value.get("name")

        if isinstance(value, str):
            text = value.strip()
            if text:
                return text

    return None


def _get_nested(payload: Mapping[str, Any], key: str) -> Any:
    value: Any = payload
    for part in key.split("."):
        if not isinstance(value, Mapping):
            return None
        value = value.get(part)
    return value


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""

    words = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    words = re.sub(r"[^A-Za-z0-9]+", " ", words)
    return " ".join(words.lower().split())


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(RESEARCH_TITLE_PREFIX.lower())
