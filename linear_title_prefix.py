"""Build Linear issue title updates for Cursor research automation.

The automation host is responsible for applying the returned action to Linear.
This module keeps the decision logic small and easy to exercise locally.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}
DIRECT_STATUS_TRIGGERS = {
    "status changed",
    "statuschanged",
    "status change",
    "state changed",
    "statechanged",
    "workflow state changed",
    "workflowstatechanged",
}
GENERIC_UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to to research."""

    if not isinstance(event, Mapping):
        return None

    payload = _payload(event)
    if not _is_status_change(payload):
        return None

    new_status = _string_value(
        _first_value(
            payload,
            (
                "newStatus",
                "new_status",
                "toStatus",
                "to_status",
                "status",
                "state.name",
                "workflowState.name",
                "workflow_state.name",
            ),
        )
    )
    if _normalize_status(new_status) != _normalize_status(TARGET_STATUS):
        return None

    issue_id = _string_value(
        _first_value(payload, ("issueId", "issue_id", "id", "identifier", "key"))
    )
    title = _string_value(_first_value(payload, ("title", "issue.title")))
    if not issue_id or not title:
        return None

    if _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _payload(event: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten the useful parts of known Cursor and Linear webhook payloads."""

    flattened: dict[str, Any] = {}

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        flattened.update(trigger_context)

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            flattened.update(issue)
        flattened.update(data)

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        flattened.update(issue)

    flattened.update(event)
    return flattened


def _is_status_change(payload: Mapping[str, Any]) -> bool:
    trigger_values = (
        payload.get("trigger"),
        payload.get("webhookType"),
        payload.get("action"),
        payload.get("type"),
    )
    normalized_triggers = {
        normalized for value in trigger_values if (normalized := _normalize_label(value))
    }

    if normalized_triggers & DIRECT_STATUS_TRIGGERS:
        return True

    if normalized_triggers & GENERIC_UPDATE_TRIGGERS:
        return _updated_status_fields(payload)

    return False


def _updated_status_fields(payload: Mapping[str, Any]) -> bool:
    updated_fields = payload.get("updatedFields")
    if updated_fields is None:
        updated_fields = payload.get("updated_fields")

    if _sequence_mentions_status(updated_fields):
        return True

    changes = payload.get("changes")
    if isinstance(changes, Mapping):
        return any(_normalize_field_name(key) in STATUS_FIELDS for key in changes)

    return False


def _sequence_mentions_status(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_field_name(value) in STATUS_FIELDS

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return any(_normalize_field_name(item) in STATUS_FIELDS for item in value)

    return False


def _first_value(payload: Mapping[str, Any], paths: Sequence[str]) -> Any:
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


def _string_value(value: Any) -> str | None:
    if value is None:
        return None

    if isinstance(value, Mapping):
        value = value.get("name") or value.get("title") or value.get("id")

    if not isinstance(value, str):
        return None

    stripped = value.strip()
    return stripped or None


def _has_prefix(title: str) -> bool:
    return title.casefold().startswith(TITLE_PREFIX.casefold())


def _normalize_status(value: Any) -> str | None:
    normalized = _normalize_label(value)
    if normalized is None:
        return None
    return normalized.replace(" ", "")


def _normalize_label(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value.strip())
    normalized = re.sub(r"[^a-z0-9]+", " ", spaced.casefold()).strip()
    return normalized or None


def _normalize_field_name(value: Any) -> str | None:
    normalized = _normalize_label(value)
    if normalized is None:
        return None
    return normalized.replace(" ", "")


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
