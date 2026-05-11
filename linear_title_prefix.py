"""Helpers for Linear issue title updates triggered by status changes."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue enters "to research".

    The automation payload shape can vary between webhook and trigger sources, so
    this accepts both flat payloads and nested `triggerContext`/`data`/`issue`
    objects while keeping the matching rules narrow.
    """

    if not isinstance(event, Mapping):
        return None

    payload = _flatten_event(event)
    if not _is_status_change_event(payload):
        return None

    new_status = _pick_text(payload, "newStatus", "new_status", "status")
    if new_status is None:
        new_status = _pick_nested_name(payload, "state", "workflowState")

    if _normalize_label(new_status) != _normalize_label(TARGET_STATUS):
        return None

    issue_id = _pick_text(payload, "id", "issueId", "issue_id", "identifier")
    title = _pick_text(payload, "title", "name")
    if issue_id is None or title is None:
        return None

    if _has_research_prefix(title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _flatten_event(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge supported nested payload locations into a single lookup map."""

    flattened: dict[str, Any] = {}

    for key in ("issue", "data", "triggerContext"):
        value = event.get(key)
        if isinstance(value, Mapping):
            flattened.update(_flatten_event(value))

    flattened.update(event)
    return flattened


def _is_status_change_event(payload: Mapping[str, Any]) -> bool:
    for key in ("trigger", "webhookType", "action", "type"):
        value = payload.get(key)
        normalized = _normalize_label(value)
        if normalized in {"status changed", "status change", "statuschanged"}:
            return True
        if normalized in {"issue updated", "updated issue"}:
            return _updated_fields_include_status(payload.get("updatedFields"))

    return False


def _updated_fields_include_status(updated_fields: Any) -> bool:
    if isinstance(updated_fields, str):
        fields = [updated_fields]
    elif isinstance(updated_fields, Mapping):
        fields = updated_fields.keys()
    elif isinstance(updated_fields, list | tuple | set):
        fields = updated_fields
    else:
        return False

    return any(
        _normalize_label(field) in {"status", "state", "workflow state", "workflowstate"}
        for field in fields
    )


def _pick_text(payload: Mapping[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str):
            text = value.strip()
            if text:
                return text
    return None


def _pick_nested_name(payload: Mapping[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, Mapping):
            name = value.get("name")
            if isinstance(name, str) and name.strip():
                return name.strip()
    return None


def _has_research_prefix(title: str) -> bool:
    return title.strip().lower().startswith(TITLE_PREFIX.lower())


def _normalize_label(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return re.sub(r"[^a-z0-9]+", " ", spaced.lower()).strip()
