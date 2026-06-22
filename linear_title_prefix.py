"""Build Linear issue-title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow status"}
_NEW_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "toStatus",
    "to_status",
    "status",
    "state",
    "workflowState",
    "workflow_state",
)
_ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "key", "id")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue-title update action when a Linear issue enters research."""

    if not isinstance(event, Mapping):
        return None

    payload = _payload_with_context(event)
    if not _is_status_change(payload):
        return None

    new_status = _extract_new_status(payload)
    if _normalize(new_status) != TARGET_STATUS:
        return None

    issue = _extract_issue(payload)
    issue_id = _first_string(issue, _ISSUE_ID_KEYS)
    title = _first_string(issue, ("title", "name"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _payload_with_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common Cursor and Linear wrappers into one payload view."""

    payload: dict[str, Any] = {}

    automation_context = _mapping_at(event, "automation_trigger_info", "triggerContext")
    if automation_context:
        payload.update(automation_context)

    trigger_context = _mapping_at(event, "triggerContext")
    if trigger_context:
        payload.update(trigger_context)

    data = event.get("data")
    if isinstance(data, Mapping):
        payload.update(data)

    payload.update(event)
    return payload


def _is_status_change(payload: Mapping[str, Any]) -> bool:
    trigger_values = _metadata_values(payload)
    if any(_is_direct_status_change(value) for value in trigger_values):
        return True

    if any(_is_update_event(value) for value in trigger_values):
        return _mentions_status_field(payload)

    return False


def _metadata_values(payload: Mapping[str, Any]) -> list[Any]:
    values: list[Any] = []
    for key in ("trigger", "webhookType", "action", "type", "event", "name"):
        if key in payload:
            values.append(payload[key])

    for wrapper_key in ("triggerContext", "automation_trigger_info", "data"):
        nested = payload.get(wrapper_key)
        if isinstance(nested, Mapping):
            values.extend(_metadata_values(nested))

    return values


def _is_direct_status_change(value: Any) -> bool:
    normalized = _normalize(value)
    return normalized in {
        "status changed",
        "state changed",
        "workflow state changed",
        "workflow status changed",
    }


def _is_update_event(value: Any) -> bool:
    normalized = _normalize(value)
    return normalized in {
        "update",
        "updated",
        "issue update",
        "issue updated",
        "updated issue",
    }


def _mentions_status_field(payload: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        fields = payload.get(key)
        if _sequence_mentions_status(fields):
            return True

    changes = payload.get("changes")
    if isinstance(changes, Mapping):
        return any(_is_status_field(key) for key in changes)
    if isinstance(changes, Sequence) and not isinstance(changes, (str, bytes, bytearray)):
        return any(_change_mentions_status(change) for change in changes)

    return False


def _sequence_mentions_status(fields: Any) -> bool:
    if isinstance(fields, str):
        return _is_status_field(fields)
    if isinstance(fields, Sequence) and not isinstance(fields, (bytes, bytearray)):
        return any(_is_status_field(field) for field in fields)
    return False


def _change_mentions_status(change: Any) -> bool:
    if isinstance(change, str):
        return _is_status_field(change)
    if isinstance(change, Mapping):
        field = change.get("field") or change.get("name") or change.get("key")
        return _is_status_field(field)
    return False


def _is_status_field(field: Any) -> bool:
    normalized = _normalize(field)
    return normalized in _STATUS_FIELD_NAMES


def _extract_new_status(payload: Mapping[str, Any]) -> Any:
    for key in _NEW_STATUS_KEYS:
        if key in payload:
            return payload[key]

    changes = payload.get("changes")
    if isinstance(changes, Mapping):
        for key, value in changes.items():
            if _is_status_field(key):
                return _change_new_value(value)
    if isinstance(changes, Sequence) and not isinstance(changes, (str, bytes, bytearray)):
        for change in changes:
            if _change_mentions_status(change):
                return _change_new_value(change)

    issue = _extract_issue(payload)
    for key in ("status", "state", "workflowState", "workflow_state"):
        if key in issue:
            return issue[key]

    return None


def _change_new_value(change: Any) -> Any:
    if isinstance(change, Mapping):
        for key in ("newValue", "new_value", "to", "after", "value", "name"):
            if key in change:
                return change[key]
    return change


def _extract_issue(payload: Mapping[str, Any]) -> dict[str, Any]:
    issue: dict[str, Any] = {}

    for key in ("issue", "data"):
        nested = payload.get(key)
        if isinstance(nested, Mapping):
            if isinstance(nested.get("issue"), Mapping):
                issue.update(nested["issue"])
            else:
                issue.update(nested)

    issue.update(payload)
    return issue


def _first_string(payload: Mapping[str, Any], keys: Sequence[str]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _mapping_at(payload: Mapping[str, Any], *path: str) -> Mapping[str, Any] | None:
    current: Any = payload
    for key in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current if isinstance(current, Mapping) else None


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def _normalize(value: Any) -> str:
    if isinstance(value, Mapping):
        for key in ("name", "title", "label", "value"):
            if key in value:
                return _normalize(value[key])
        return ""
    if not isinstance(value, str):
        return ""

    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    spaced = re.sub(r"[^A-Za-z0-9]+", " ", spaced)
    return " ".join(spaced.lower().split())


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
