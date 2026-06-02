"""Build Linear issue title updates for Cursor research automation."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


CURSOR_RESEARCHING_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"

_CONTAINER_KEYS = ("triggerContext", "data", "issue")
_ISSUE_DETAIL_KEYS = {
    "id",
    "issueId",
    "issue_id",
    "identifier",
    "title",
    "name",
    "state",
    "status",
    "workflowState",
    "workflow_state",
}
_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "state id",
    "stateid",
    "workflow state",
    "workflowstate",
    "workflow state id",
    "workflowstateid",
}
_STATUS_CHANGE_TRIGGERS = {
    "status changed",
    "status change",
    "statuschanged",
    "state changed",
    "state change",
    "statechanged",
    "workflow state changed",
    "workflowstatechanged",
}
_UPDATE_ACTIONS = {"update", "updated", "issue updated", "updated issue"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update when an issue moves to To Research."""
    if not isinstance(event, Mapping):
        return None

    payload = _flatten_event(event)
    if not _is_status_change_event(payload):
        return None

    status = _new_status(payload)
    if _normalize_value(status) != _normalize_value(TARGET_STATUS):
        return None

    issue_id = _first_text(payload, "id", "issueId", "issue_id", "identifier")
    title = _first_text(payload, "title", "name")
    if not issue_id or not title:
        return None

    if _has_cursor_researching_prefix(title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id,
        "title": f"{CURSOR_RESEARCHING_PREFIX}: {title}",
    }


def _flatten_event(event: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten common Linear webhook and Cursor automation payload wrappers."""
    payload: dict[str, Any] = {}

    for key in _CONTAINER_KEYS:
        value = event.get(key)
        if isinstance(value, Mapping):
            payload.update(_flatten_event(value))

    for key, value in event.items():
        if key in _CONTAINER_KEYS:
            continue

        # Nested Linear issue data is more specific than outer webhook metadata.
        if key in _ISSUE_DETAIL_KEYS and key in payload:
            continue

        payload[key] = value

    return payload


def _is_status_change_event(payload: Mapping[str, Any]) -> bool:
    for key in ("trigger", "event", "eventType", "type", "webhookType"):
        trigger = _first_text(payload, key)
        if _normalize_value(trigger) in _STATUS_CHANGE_TRIGGERS:
            return True

    action = _normalize_value(_first_text(payload, "action"))
    if action in _UPDATE_ACTIONS:
        return any(
            _contains_status_field(payload.get(key))
            for key in ("updatedFields", "updated_fields", "updatedFrom", "updated_from", "changes")
        )

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_value(value) in _STATUS_FIELD_NAMES

    if isinstance(value, Mapping):
        return any(
            _contains_status_field(key) or _contains_status_field(item)
            for key, item in value.items()
        )

    if isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray, str)):
        return any(_contains_status_field(item) for item in value)

    return False


def _new_status(payload: Mapping[str, Any]) -> str | None:
    status = _first_text(
        payload,
        "newStatus",
        "new_status",
        "toStatus",
        "to_status",
        "newState",
        "new_state",
        "stateName",
        "status",
    )
    if status is not None:
        return status

    for key in ("state", "workflowState", "workflow_state", "status"):
        value = payload.get(key)
        if isinstance(value, Mapping):
            status = _first_text(value, "name", "title")
            if status is not None:
                return status
        elif isinstance(value, str):
            status = value.strip()
            if status:
                return status

    return None


def _first_text(payload: Mapping[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str):
            text = value.strip()
            if text:
                return text
    return None


def _normalize_value(value: str | None) -> str:
    if not value:
        return ""

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return re.sub(r"[^a-z0-9]+", " ", spaced.lower()).strip()


def _has_cursor_researching_prefix(title: str) -> bool:
    return title.lstrip().lower().startswith(CURSOR_RESEARCHING_PREFIX.lower())


def main() -> int:
    """Read a Linear event JSON payload from stdin and print a title update."""
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON payload: {exc}", file=sys.stderr)
        return 1

    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
