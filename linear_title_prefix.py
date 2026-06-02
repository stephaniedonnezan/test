"""Build Linear issue title updates for research status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}
STATUS_TRIGGER_VALUES = {
    "status changed",
    "status change",
    "status updated",
    "state changed",
    "workflow state changed",
}
UPDATE_TRIGGER_VALUES = {
    "issue updated",
    "updated issue",
    "update",
    "updated",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to research."""

    if not isinstance(event, Mapping):
        return None

    payload = _normalized_payload(event)
    if not _is_status_change_event(payload):
        return None

    status = _new_status(payload)
    if _normalize_text(status) != TARGET_STATUS:
        return None

    issue_id = _first_string(payload, ("id", "issueId", "issue_id", "identifier"))
    title = _first_string(payload, ("title", "name"))
    if not issue_id or not title:
        return None

    clean_title = title.strip()
    if _has_prefix(clean_title):
        prefixed_title = clean_title
    else:
        prefixed_title = f"{TITLE_PREFIX}: {clean_title}"

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": prefixed_title,
    }


def _normalized_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common wrapper fields so flat automation and Linear payloads work."""

    payload: dict[str, Any] = {}

    issue = _mapping_at(event, "issue")
    data = _mapping_at(event, "data")
    trigger_context = _mapping_at(event, "triggerContext")

    if data:
        data_issue = _mapping_at(data, "issue")
        if data_issue:
            payload.update(data_issue)
        payload.update(data)

    if issue:
        payload.update(issue)

    if trigger_context:
        context_issue = _mapping_at(trigger_context, "issue")
        context_data = _mapping_at(trigger_context, "data")
        if context_data:
            context_data_issue = _mapping_at(context_data, "issue")
            if context_data_issue:
                payload.update(context_data_issue)
            payload.update(context_data)
        if context_issue:
            payload.update(context_issue)
        payload.update(trigger_context)

    payload.update(event)
    return payload


def _is_status_change_event(payload: Mapping[str, Any]) -> bool:
    trigger_values = [
        _normalize_text(value)
        for key in ("trigger", "webhookType", "action", "type")
        for value in _string_values(payload.get(key))
    ]

    if any(value in STATUS_TRIGGER_VALUES for value in trigger_values):
        return True

    if any(value in UPDATE_TRIGGER_VALUES for value in trigger_values):
        return _updated_fields_include_status(payload)

    return False


def _updated_fields_include_status(payload: Mapping[str, Any]) -> bool:
    fields = payload.get("updatedFields")
    if fields is None:
        fields = payload.get("updated_fields")

    for field in _string_values(fields):
        if _normalize_field_name(field) in STATUS_FIELDS:
            return True

    return False


def _new_status(payload: Mapping[str, Any]) -> str | None:
    for key in ("newStatus", "new_status", "status"):
        value = _status_name(payload.get(key))
        if value:
            return value

    for key in ("state", "workflowState", "workflow_state"):
        value = _status_name(payload.get(key))
        if value:
            return value

    return None


def _status_name(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        return _first_string(value, ("name", "title", "status"))
    return None


def _mapping_at(payload: Mapping[str, Any], key: str) -> Mapping[str, Any] | None:
    value = payload.get(key)
    return value if isinstance(value, Mapping) else None


def _first_string(payload: Mapping[str, Any], keys: Sequence[str]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _string_values(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, Mapping):
        return [item for item in value.values() if isinstance(item, str)]
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [item for item in value if isinstance(item, str)]
    return []


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""

    separated = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    return re.sub(r"[\W_]+", " ", separated).strip().casefold()


def _normalize_field_name(value: str) -> str:
    return re.sub(r"[\W_]+", "", value).casefold()


def _has_prefix(title: str) -> bool:
    normalized_title = title.casefold()
    normalized_prefix = TITLE_PREFIX.casefold()
    return normalized_title == normalized_prefix or normalized_title.startswith(
        f"{normalized_prefix}:"
    )


def main() -> int:
    """Read an event JSON document from stdin and print the action as JSON."""

    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is None:
        return 0

    print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
