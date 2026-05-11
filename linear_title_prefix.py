"""Helpers for updating Linear issue titles during research transitions."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Build a title update for Linear issues moved into To Research.

    The automation runner is expected to call this function with the Linear
    webhook payload and apply the returned update action when it is not None.
    """
    if not isinstance(event, Mapping):
        return None

    context = _combined_context(event)
    if not _is_status_change(context):
        return None

    if _normalize(context.get("newStatus") or context.get("new_status")) != TARGET_STATUS:
        status = _status_name(context.get("state")) or _status_name(context.get("workflowState"))
        if _normalize(status or context.get("status")) != TARGET_STATUS:
            return None

    issue_id = _first_text(context, "issueId", "issue_id", "identifier", "id")
    title = _first_text(context, "title", "name")
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _combined_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common Linear payload nesting styles into one lookup dictionary."""
    context: dict[str, Any] = {}

    data = _mapping(event.get("data"))
    issue = _mapping(data.get("issue")) or _mapping(event.get("issue"))
    trigger_context = _mapping(event.get("triggerContext"))

    for source in (event, data, issue, trigger_context):
        context.update(source)

    return context


def _is_status_change(context: Mapping[str, Any]) -> bool:
    trigger_value = (
        context.get("trigger")
        or context.get("action")
        or context.get("type")
        or context.get("webhookType")
    )
    normalized_trigger = _normalize(trigger_value)

    if normalized_trigger in {
        "status changed",
        "status change",
        "state changed",
        "workflow state changed",
    }:
        return True

    updated_fields = context.get("updatedFields") or context.get("updated_fields")
    if isinstance(updated_fields, str):
        updated_fields = [updated_fields]

    if isinstance(updated_fields, list):
        return any(
            _normalize(field) in {"status", "state", "state id", "workflow state", "workflow state id"}
            for field in updated_fields
        )

    return False


def _first_text(context: Mapping[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = context.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _status_name(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        name = value.get("name")
        if isinstance(name, str):
            return name
    return None


def _normalize(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    value = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    value = re.sub(r"[^a-zA-Z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip().lower()
