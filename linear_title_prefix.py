"""Build Linear issue title updates for research-status automations."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title-update instruction when an issue moves to research."""
    if not isinstance(event, Mapping):
        return None

    payload = _flatten_event(event)
    if not _is_status_change(payload):
        return None

    status = _first_present(payload, "newStatus", "new_status", "status", "state")
    if _normalize_label(status) != TARGET_STATUS:
        return None

    issue_id = _as_text(
        _first_present(payload, "id", "issueId", "issue_id", "identifier")
    )
    title = _as_text(_first_present(payload, "title", "name"))
    if not issue_id or not title:
        return None

    if _has_prefix(title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _flatten_event(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common Linear webhook nesting levels, keeping outer trigger data."""
    flattened: dict[str, Any] = {}

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        flattened.update(_issue_payload(trigger_context))

    data = event.get("data")
    if isinstance(data, Mapping):
        flattened.update(_issue_payload(data))

    flattened.update(_issue_payload(event))
    return flattened


def _issue_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    issue = payload.get("issue")
    fields = dict(issue) if isinstance(issue, Mapping) else {}
    fields.update(payload)

    state = fields.get("state")
    if isinstance(state, Mapping):
        state_name = _first_present(state, "name", "title")
        if state_name is not None:
            fields.setdefault("state", state_name)

    return fields


def _is_status_change(payload: Mapping[str, Any]) -> bool:
    triggers = [
        _normalize_label(payload.get(key))
        for key in ("trigger", "webhookType", "action", "type")
    ]
    if any(
        trigger in {"status changed", "statuschanged", "issue status changed"}
        for trigger in triggers
    ):
        return True

    if "issue updated" in triggers:
        updated_fields = payload.get("updatedFields") or payload.get("updated_fields")
        if isinstance(updated_fields, Mapping):
            updated_fields = updated_fields.keys()

        if isinstance(updated_fields, str):
            return _normalize_label(updated_fields) in {"status", "state"}

        if isinstance(updated_fields, list | tuple | set):
            return any(
                _normalize_label(field) in {"status", "state"}
                for field in updated_fields
            )

    return False


def _first_present(payload: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        value = payload.get(key)
        if value is not None:
            return value
    return None


def _as_text(value: Any) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    return text or None


def _normalize_label(value: Any) -> str:
    if isinstance(value, Mapping):
        value = _first_present(value, "name", "title")
    if value is None:
        return ""

    text = str(value).strip()
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^a-zA-Z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())
