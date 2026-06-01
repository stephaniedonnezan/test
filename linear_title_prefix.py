"""Build Linear issue title updates for Cursor research automations."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow state"}


def build_issue_title_update(event: Any) -> dict[str, str] | None:
    """Return a Linear title update action when an issue enters research."""
    payload = _event_payload(event)
    if payload is None or not _is_status_change_event(payload):
        return None

    status = _new_status(payload)
    if _normalize_value(status) != TARGET_STATUS:
        return None

    issue_id = _first_text(payload, ("id", "issueId", "issue_id", "identifier"))
    title = _first_text(payload, ("title", "name"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_title_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _event_payload(event: Any) -> dict[str, Any] | None:
    if not isinstance(event, Mapping):
        return None

    payload: dict[str, Any] = {}
    for key in ("issue", "data", "triggerContext"):
        value = event.get(key)
        if isinstance(value, Mapping):
            payload.update(_event_payload(value) or {})

    nested_data = event.get("data")
    if isinstance(nested_data, Mapping):
        nested_issue = nested_data.get("issue")
        if isinstance(nested_issue, Mapping):
            payload.update(_event_payload(nested_issue) or {})

    payload.update(event)
    return payload


def _is_status_change_event(payload: Mapping[str, Any]) -> bool:
    trigger_values = [
        _normalize_value(value)
        for key, value in payload.items()
        if key in {"trigger", "webhookType", "action", "type"} and isinstance(value, str)
    ]

    if any(value in {"status changed", "state changed", "status change", "state change"} for value in trigger_values):
        return True

    if any(value in {"issue updated", "updated issue", "update", "updated"} for value in trigger_values):
        updated_fields = _updated_fields(payload)
        return bool(updated_fields & STATUS_FIELD_NAMES)

    return False


def _updated_fields(payload: Mapping[str, Any]) -> set[str]:
    values: set[str] = set()
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        field_value = payload.get(key)
        if isinstance(field_value, str):
            values.add(_normalize_value(field_value))
        elif isinstance(field_value, Mapping):
            values.update(_normalize_value(str(field)) for field in field_value)
        elif isinstance(field_value, list | tuple | set):
            values.update(_normalize_value(str(field)) for field in field_value)
    return values


def _new_status(payload: Mapping[str, Any]) -> str | None:
    for key in (
        "newStatus",
        "new_status",
        "statusName",
        "status_name",
        "stateName",
        "state_name",
        "workflowStateName",
        "workflow_state_name",
    ):
        value = payload.get(key)
        if isinstance(value, str):
            return value

    for key in ("status", "state", "workflowState", "workflow_state"):
        value = payload.get(key)
        if isinstance(value, str):
            return value
        if isinstance(value, Mapping):
            name = value.get("name")
            if isinstance(name, str):
                return name

    return None


def _first_text(payload: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _has_title_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def _normalize_value(value: Any) -> str:
    text = str(value).strip()
    text = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", text)
    text = re.sub(r"[_\-\s]+", " ", text)
    return text.lower()


def main() -> int:
    update = build_issue_title_update(json.load(sys.stdin))
    if update is not None:
        print(json.dumps(update))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
