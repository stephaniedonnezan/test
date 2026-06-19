"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow_status"}
DIRECT_STATUS_TRIGGERS = {
    "status changed",
    "status updated",
    "state changed",
    "workflow state changed",
}
GENERIC_UPDATE_TRIGGERS = {"update", "updated", "issue updated", "updated issue"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to research.

    The Cursor automation trigger can provide a compact ``triggerContext`` shape,
    while Linear webhooks usually nest issue data below ``data``. This function
    accepts either form and returns a small action object for the caller to apply.
    """

    if not isinstance(event, Mapping):
        return None

    payload = _flatten_payload(event)
    if not _is_status_change_event(payload):
        return None

    new_status = _find_new_status(payload)
    if _normalize_text(new_status) != TARGET_STATUS:
        return None

    title = _clean_string(_first_value(payload, ("title", "name")))
    issue_id = _clean_string(
        _first_value(payload, ("issueId", "issue_id", "identifier", "key", "id"))
    )
    if not title or not issue_id:
        return None

    if title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _flatten_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common wrapper objects with outer fields taking precedence."""

    flattened: dict[str, Any] = {}

    def visit(value: Any) -> None:
        if not isinstance(value, Mapping):
            return
        for key in ("triggerContext", "webhook", "data", "issue"):
            nested = value.get(key)
            if isinstance(nested, Mapping):
                visit(nested)
        flattened.update(value)

    visit(event)
    return flattened


def _is_status_change_event(payload: Mapping[str, Any]) -> bool:
    trigger_values = [
        _normalize_text(payload.get(key))
        for key in ("trigger", "webhookType", "action", "type", "event")
    ]

    if any(value in DIRECT_STATUS_TRIGGERS for value in trigger_values):
        return True

    if any(value in GENERIC_UPDATE_TRIGGERS for value in trigger_values):
        return _updated_fields_include_status(payload)

    return False


def _updated_fields_include_status(payload: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        if _field_collection_includes_status(payload.get(key)):
            return True

    changes = payload.get("changes")
    if isinstance(changes, Mapping):
        return any(_field_name_is_status(field) for field in changes)

    return _field_collection_includes_status(changes)


def _field_collection_includes_status(value: Any) -> bool:
    if isinstance(value, str):
        return _field_name_is_status(value)

    if isinstance(value, Mapping):
        return any(_field_name_is_status(field) for field in value)

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return any(_field_name_is_status(item) for item in value)

    return False


def _field_name_is_status(value: Any) -> bool:
    normalized = _normalize_key(value)
    return normalized in STATUS_FIELD_NAMES or normalized.endswith("status")


def _find_new_status(payload: Mapping[str, Any]) -> str | None:
    explicit_status = _first_value(
        payload,
        (
            "newStatus",
            "new_status",
            "toStatus",
            "to_status",
            "statusName",
            "status_name",
            "stateName",
            "state_name",
            "workflowStateName",
            "workflow_state_name",
        ),
    )
    if explicit_status is not None:
        return _status_name(explicit_status)

    changes = payload.get("changes")
    if isinstance(changes, Mapping):
        for key, value in changes.items():
            if _field_name_is_status(key):
                next_value = value.get("to") if isinstance(value, Mapping) else value
                return _status_name(next_value)

    for key in ("status", "state", "workflowState", "workflow_state"):
        status = _status_name(payload.get(key))
        if status:
            return status

    return None


def _status_name(value: Any) -> str | None:
    if isinstance(value, Mapping):
        return _clean_string(
            _first_value(value, ("name", "title", "label", "status", "state"))
        )
    return _clean_string(value)


def _first_value(payload: Mapping[str, Any], keys: Sequence[str]) -> Any:
    for key in keys:
        if key in payload and payload[key] is not None:
            return payload[key]
    return None


def _clean_string(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return re.sub(r"[^a-z0-9]+", " ", spaced.lower()).strip()


def _normalize_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", _normalize_text(value))


def main() -> int:
    action = build_issue_title_update(json.load(sys.stdin))
    if action is not None:
        print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
