"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update payload when a Linear issue moves to research."""
    if not isinstance(event, Mapping):
        return None

    payload = _flatten_event(event)
    if not _is_status_change(payload):
        return None

    status = _first_value(payload, ("newStatus", "new_status", "status"))
    if status is None:
        status = _nested_name(payload.get("state"))

    if _normalize_status(status) != "to research":
        return None

    issue_id = _first_value(payload, ("id", "issueId", "issue_id", "identifier"))
    title = _first_value(payload, ("title", "name"))
    if not isinstance(issue_id, str) or not isinstance(title, str):
        return None

    stripped_title = title.strip()
    if not stripped_title:
        return None

    if stripped_title.lower().startswith(PREFIX.lower()):
        updated_title = stripped_title
    else:
        updated_title = f"{PREFIX}: {stripped_title}"

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": updated_title,
    }


def _flatten_event(event: Mapping[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        payload.update(_flatten_event(trigger_context))

    data = event.get("data")
    if isinstance(data, Mapping):
        payload.update(_flatten_event(data))

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        payload.update(_flatten_event(issue))

    # Outer fields are the freshest webhook metadata, so let them override
    # same-named fields from nested issue objects.
    for key, value in event.items():
        if key not in {"triggerContext", "data", "issue"}:
            payload[key] = value

    return payload


def _is_status_change(payload: Mapping[str, Any]) -> bool:
    trigger = _first_value(payload, ("trigger", "webhookType", "action", "type"))
    normalized_trigger = _normalize_token(trigger)
    if normalized_trigger in {
        "statuschanged",
        "statuschange",
        "statuschangedissue",
    }:
        return True

    if normalized_trigger in {"issueupdated", "updatedissue"}:
        return _updated_fields_include_status(payload.get("updatedFields"))

    return _updated_fields_include_status(payload.get("updatedFields"))


def _updated_fields_include_status(updated_fields: Any) -> bool:
    if isinstance(updated_fields, str):
        return _normalize_token(updated_fields) in {"status", "state"}

    if isinstance(updated_fields, Mapping):
        return any(
            _normalize_token(field_name) in {"status", "state"}
            for field_name in updated_fields.keys()
        )

    if isinstance(updated_fields, (list, tuple, set, frozenset)):
        return any(
            _normalize_token(field_name) in {"status", "state"}
            for field_name in updated_fields
        )

    return False


def _first_value(payload: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in payload and payload[key] is not None:
            return payload[key]
    return None


def _nested_name(value: Any) -> Any:
    if isinstance(value, Mapping):
        return value.get("name")
    return None


def _normalize_status(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return re.sub(r"[^a-z0-9]+", " ", spaced.lower()).strip()


def _normalize_token(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    return re.sub(r"[^a-z0-9]+", "", value.lower())
