"""Build title update actions for Linear issues moved into research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = frozenset({"status", "state", "workflowstate", "workflow_state"})
STATUS_TRIGGER_VALUES = frozenset(
    {
        "statuschanged",
        "statuschange",
        "statusupdated",
        "statechanged",
        "statechange",
        "workflowstatechanged",
        "workflowstatechange",
    }
)
ISSUE_UPDATE_VALUES = frozenset(
    {
        "update",
        "updated",
        "issueupdate",
        "issueupdated",
        "updatedissue",
    }
)


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear issue title update action when an issue enters research.

    The automation can receive either a flattened Cursor triggerContext payload or
    a nested Linear webhook event. Returning a simple action keeps this module
    side-effect free while letting the caller perform the actual Linear update.
    """

    if not isinstance(event, Mapping):
        return None

    payload = _coerce_payload(event)
    if not _is_status_change_event(payload):
        return None

    new_status = _extract_new_status(payload)
    if _normalize_words(new_status) != _normalize_words(TARGET_STATUS):
        return None

    title = _extract_text(payload, ("title", "name"))
    issue_id = _extract_text(payload, ("issueId", "issue_id", "id", "identifier", "key"))
    if not title or not issue_id:
        return None

    if title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _coerce_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}

    for key in ("triggerContext", "webhook", "data", "issue"):
        value = event.get(key)
        if isinstance(value, Mapping):
            payload.update(_coerce_payload(value))

    payload.update(event)
    return payload


def _is_status_change_event(payload: Mapping[str, Any]) -> bool:
    trigger_values = _collect_trigger_values(payload)
    if any(value in STATUS_TRIGGER_VALUES for value in trigger_values):
        return True

    if any(value in ISSUE_UPDATE_VALUES for value in trigger_values):
        return _updated_fields_include_status(payload)

    return False


def _collect_trigger_values(payload: Mapping[str, Any]) -> set[str]:
    values: set[str] = set()
    for key in ("trigger", "webhookType", "action", "type", "eventType"):
        raw_value = payload.get(key)
        if isinstance(raw_value, str):
            values.add(_normalize_token(raw_value))
    return values


def _updated_fields_include_status(payload: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        if _field_collection_includes_status(payload.get(key)):
            return True

    changes = payload.get("changes") or payload.get("changed")
    if isinstance(changes, Mapping):
        return any(_normalize_field_name(key) in STATUS_FIELDS for key in changes)

    return False


def _field_collection_includes_status(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_field_name(value) in STATUS_FIELDS

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return any(_normalize_field_name(field) in STATUS_FIELDS for field in value)

    return False


def _extract_new_status(payload: Mapping[str, Any]) -> str | None:
    for key in ("newStatus", "new_status", "statusName", "stateName", "workflowStateName"):
        value = _extract_status_name(payload.get(key))
        if value:
            return value

    changes = payload.get("changes") or payload.get("changed")
    if isinstance(changes, Mapping):
        for key in ("status", "state", "workflowState", "workflow_state"):
            value = changes.get(key)
            if isinstance(value, Mapping):
                status = _extract_status_name(
                    value.get("new")
                    or value.get("to")
                    or value.get("newValue")
                    or value.get("after")
                )
            else:
                status = _extract_status_name(value)
            if status:
                return status

    for key in ("status", "state", "workflowState", "workflow_state"):
        value = _extract_status_name(payload.get(key))
        if value:
            return value

    return None


def _extract_status_name(value: Any) -> str | None:
    if isinstance(value, str):
        status = value.strip()
        return status or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            status = _extract_status_name(value.get(key))
            if status:
                return status

    return None


def _extract_text(payload: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str):
            text = value.strip()
            if text:
                return text

    return None


def _normalize_field_name(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return _normalize_token(value).replace("field", "")


def _normalize_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", _split_camel(value).lower())


def _normalize_words(value: str | None) -> str:
    if value is None:
        return ""
    return " ".join(re.findall(r"[a-z0-9]+", _split_camel(value).lower()))


def _split_camel(value: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON payload: {exc}", file=sys.stderr)
        return 1

    action = build_issue_title_update(event)
    if action is None:
        return 0

    print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
