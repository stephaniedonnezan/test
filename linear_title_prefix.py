"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
PREFIXED_TITLE = f"{PREFIX}: "
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to To Research."""
    if not isinstance(event, Mapping):
        return None

    payload = _flatten_event(event)
    if not _is_status_change(event, payload):
        return None

    new_status = _find_new_status(event, payload)
    if _normalize_value(new_status) != TARGET_STATUS:
        return None

    issue_id = _find_issue_id(payload)
    title = _clean_string(payload.get("title"))
    if not issue_id or not title or _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIXED_TITLE}{title}",
    }


def _flatten_event(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common automation and Linear webhook layers into one lookup map."""
    payload: dict[str, Any] = {}

    for key in ("issue", "data", "triggerContext"):
        value = event.get(key)
        if isinstance(value, Mapping):
            payload.update(_flatten_event(value))

    issue = payload.get("issue")
    if isinstance(issue, Mapping):
        payload.update(_flatten_event(issue))

    payload.update(event)
    return payload


def _is_status_change(event: Mapping[str, Any], payload: Mapping[str, Any]) -> bool:
    trigger_values = [
        value
        for key in ("trigger", "webhookType", "action", "type")
        for value in _collect_values(event, key)
    ]
    normalized_triggers = {_normalize_value(value) for value in trigger_values}

    if any(value in {"status changed", "statuschanged"} for value in normalized_triggers):
        return True

    if any(value in {"update", "updated", "issue updated", "updated issue"} for value in normalized_triggers):
        return _mentions_status_field(payload)

    return _mentions_status_field(payload) and _find_new_status(event, payload) is not None


def _mentions_status_field(payload: Mapping[str, Any]) -> bool:
    updated_fields = payload.get("updatedFields") or payload.get("updated_fields")
    if isinstance(updated_fields, str):
        updated_fields = [updated_fields]

    if isinstance(updated_fields, list) and any(_is_status_field(field) for field in updated_fields):
        return True

    changes = payload.get("changes") or payload.get("changedFields") or payload.get("changed_fields")
    if isinstance(changes, Mapping):
        return any(_is_status_field(field) for field in changes)
    if isinstance(changes, list):
        return any(_change_mentions_status(change) for change in changes)

    return False


def _change_mentions_status(change: Any) -> bool:
    if isinstance(change, str):
        return _is_status_field(change)
    if isinstance(change, Mapping):
        field = change.get("field") or change.get("name") or change.get("key")
        return _is_status_field(field)
    return False


def _is_status_field(value: Any) -> bool:
    return _normalize_field(value) in STATUS_FIELDS


def _find_new_status(event: Mapping[str, Any], payload: Mapping[str, Any]) -> str | None:
    for key in ("newStatus", "new_status", "statusName", "status_name"):
        status = _status_name(payload.get(key))
        if status:
            return status

    status_from_changes = _status_from_changes(payload.get("changes"))
    if status_from_changes:
        return status_from_changes

    for key in ("status", "state", "workflowState", "workflow_state"):
        status = _status_name(payload.get(key))
        if status:
            return status

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        return _find_new_status(trigger_context, trigger_context)

    return None


def _status_from_changes(changes: Any) -> str | None:
    if isinstance(changes, Mapping):
        for field, change in changes.items():
            if _is_status_field(field):
                status = _status_name(change)
                if status:
                    return status
        return None

    if isinstance(changes, list):
        for change in changes:
            if not isinstance(change, Mapping) or not _change_mentions_status(change):
                continue
            for key in ("newValue", "new_value", "to", "after", "value"):
                status = _status_name(change.get(key))
                if status:
                    return status

    return None


def _status_name(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("name", "title", "value"):
            status = _clean_string(value.get(key))
            if status:
                return status
        return None
    return _clean_string(value)


def _find_issue_id(payload: Mapping[str, Any]) -> str | None:
    for key in ("identifier", "issueId", "issue_id", "key", "id"):
        issue_id = _clean_string(payload.get(key))
        if issue_id:
            return issue_id
    return None


def _collect_values(value: Any, target_key: str) -> list[Any]:
    values: list[Any] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            if key == target_key:
                values.append(child)
            values.extend(_collect_values(child, target_key))
    elif isinstance(value, list):
        for child in value:
            values.extend(_collect_values(child, target_key))
    return values


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())


def _normalize_field(value: Any) -> str:
    return re.sub(r"[^a-z]", "", _normalize_value(value))


def _normalize_value(value: Any) -> str:
    text = _clean_string(value)
    if not text:
        return ""
    text = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", text)
    text = re.sub(r"[_-]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text.casefold()


def _clean_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value or None


def main() -> int:
    update = build_issue_title_update(json.load(sys.stdin))
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
