"""Helpers for Linear issue title updates triggered by status changes."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Build a Linear issue title update for issues moved to "to research".

    Automation payloads may be flat or may carry issue fields under common
    nested objects such as ``triggerContext``, ``data``, or ``issue``.
    """

    if not isinstance(event, Mapping):
        return None

    payload = _merge_context(event)
    if not _is_status_change(payload):
        return None

    status = _first_present(payload, "newStatus", "new_status", "status")
    if status is None and isinstance(payload.get("state"), Mapping):
        status = payload["state"].get("name")

    if _normalize(status) != _normalize(TARGET_STATUS):
        return None

    issue_id = _first_present(payload, "id", "issueId", "issue_id")
    title = _first_present(payload, "title", "name")
    if not isinstance(issue_id, str) or not issue_id.strip():
        return None
    if not isinstance(title, str) or not title.strip():
        return None

    clean_title = title.strip()
    if clean_title.casefold().startswith(PREFIX.casefold()):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {clean_title}",
    }


def _merge_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common nested automation payload objects with outer metadata."""

    merged: dict[str, Any] = dict(event)
    for key in ("triggerContext", "data", "issue"):
        nested = event.get(key)
        if isinstance(nested, Mapping):
            merged = _merge_nested_context(merged, nested)
    return merged


def _merge_nested_context(base: dict[str, Any], nested: Mapping[str, Any]) -> dict[str, Any]:
    merged = dict(nested)
    for key in ("data", "issue"):
        inner = nested.get(key)
        if isinstance(inner, Mapping):
            merged = _merge_nested_context(merged, inner)
    merged.update(base)
    return merged


def _is_status_change(payload: Mapping[str, Any]) -> bool:
    for key in ("trigger", "webhookType", "action", "type"):
        value = payload.get(key)
        if _normalize(value) == "status changed":
            return True
    return False


def _first_present(payload: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        value = payload.get(key)
        if value is not None:
            return value
    return None


def _normalize(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", value)
    normalized = re.sub(r"[_\-\s]+", " ", normalized).strip().casefold()
    return normalized
