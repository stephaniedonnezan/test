"""Helpers for adding a Cursor research prefix to Linear issue titles."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


RESEARCH_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Build a Linear title-update action for issues moved to research."""
    payload = _merge_linear_payload(event)
    if payload is None:
        return None

    if not _is_status_change_event(payload):
        return None

    if _normalized_words(_new_status(payload)) != TARGET_STATUS:
        return None

    issue_id = _string_value(_first_present(payload, "id", "issueId", "issue_id", "identifier"))
    title = _string_value(_first_present(payload, "title", "issueTitle", "issue_title", "name"))
    if not issue_id or not title:
        return None

    stripped_title = title.strip()
    if _has_research_prefix(stripped_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{RESEARCH_PREFIX}: {stripped_title}",
    }


def _merge_linear_payload(event: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(event, Mapping):
        return None

    merged: dict[str, Any] = {}
    _merge_known_child(merged, event.get("issue"))
    _merge_known_child(merged, event.get("data"))
    _merge_known_child(merged, event.get("triggerContext"))
    _merge_without_automation_metadata(merged, event)
    return merged


def _merge_known_child(merged: dict[str, Any], value: Any) -> None:
    if not isinstance(value, Mapping):
        return

    _merge_known_child(merged, value.get("issue"))
    _merge_known_child(merged, value.get("data"))
    _merge_known_child(merged, value.get("triggerContext"))
    merged.update(value)


def _merge_without_automation_metadata(merged: dict[str, Any], value: Mapping[str, Any]) -> None:
    for key, item in value.items():
        if key in {"automationId", "triggerContext", "issue", "data"}:
            continue
        merged[key] = item


def _is_status_change_event(payload: Mapping[str, Any]) -> bool:
    trigger = _first_present(payload, "trigger", "webhookType", "action", "type")
    if trigger is not None:
        normalized_trigger = _normalized_words(trigger)
        if normalized_trigger in {
            "status changed",
            "status change",
            "state changed",
            "state change",
        }:
            return True

        if normalized_trigger == "issue updated":
            return _updated_fields_include_status(payload)

        return False

    return _updated_fields_include_status(payload) or _new_status(payload) is not None


def _updated_fields_include_status(payload: Mapping[str, Any]) -> bool:
    updated_fields = _first_present(payload, "updatedFields", "updated_fields", "changedFields")
    if isinstance(updated_fields, str):
        fields = [updated_fields]
    elif isinstance(updated_fields, Mapping):
        fields = updated_fields.keys()
    elif isinstance(updated_fields, list | tuple | set):
        fields = updated_fields
    else:
        return False

    return any(_normalized_words(field) in {"status", "state"} for field in fields)


def _new_status(payload: Mapping[str, Any]) -> Any:
    state = payload.get("state")
    state_name = state.get("name") if isinstance(state, Mapping) else None
    return _first_present(payload, "newStatus", "new_status", "status", "stateName") or state_name


def _first_present(payload: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        value = payload.get(key)
        if value is not None:
            return value
    return None


def _string_value(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    return None


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(RESEARCH_PREFIX.lower())


def _normalized_words(value: Any) -> str:
    if not isinstance(value, str):
        value = str(value)

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return re.sub(r"[^a-z0-9]+", " ", spaced.lower()).strip()
