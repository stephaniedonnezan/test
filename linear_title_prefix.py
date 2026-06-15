"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow status", "workflow_status"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to research."""
    if not isinstance(event, Mapping):
        return None

    payload = _payload_from(event)
    if not _is_status_change_event(payload):
        return None

    status = _extract_new_status(payload)
    if _normalize_text(status) != TARGET_STATUS:
        return None

    issue_id = _first_string(payload, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_string(payload, ("title", "name"))
    if not issue_id or not title:
        return None

    if title.lower().startswith(PREFIX.lower()):
        new_title = title
    else:
        new_title = f"{PREFIX}: {title}"

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": new_title,
    }


def _payload_from(event: Mapping[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            payload.update(issue)
        payload.update(data)

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        payload.update(issue)

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        payload.update(trigger_context)

    payload.update(event)
    return payload


def _is_status_change_event(payload: Mapping[str, Any]) -> bool:
    marker_values = [
        payload.get("trigger"),
        payload.get("webhookType"),
        payload.get("action"),
        payload.get("type"),
    ]
    normalized_markers = {_normalize_marker(value) for value in marker_values if value is not None}

    if normalized_markers & {"statuschanged", "statuschange", "statechanged", "workflowstatechanged"}:
        return True

    if normalized_markers & {"issueupdated", "updatedissue", "update"}:
        return _updated_status_field(payload)

    return _updated_status_field(payload)


def _updated_status_field(payload: Mapping[str, Any]) -> bool:
    for field_name in ("updatedFields", "changedFields"):
        if _contains_status_field(payload.get(field_name)):
            return True

    changes = payload.get("changes")
    if isinstance(changes, Mapping):
        return any(_normalize_text(key) in STATUS_FIELDS for key in changes)
    if isinstance(changes, list):
        for change in changes:
            if isinstance(change, Mapping):
                field = change.get("field") or change.get("name") or change.get("fieldName")
                if _normalize_text(field) in STATUS_FIELDS:
                    return True
            elif _normalize_text(change) in STATUS_FIELDS:
                return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_text(value) in STATUS_FIELDS
    if isinstance(value, list | tuple | set):
        return any(_contains_status_field(item) for item in value)
    return False


def _extract_new_status(payload: Mapping[str, Any]) -> str | None:
    direct_status = _first_string(
        payload,
        (
            "newStatus",
            "new_status",
            "toStatus",
            "to_status",
            "statusName",
            "stateName",
            "workflowStateName",
        ),
    )
    if direct_status:
        return direct_status

    status_from_changes = _status_from_changes(payload.get("changes"))
    if status_from_changes:
        return status_from_changes

    for field_name in ("status", "state", "workflowState"):
        status = _string_or_name(payload.get(field_name))
        if status:
            return status

    return None


def _status_from_changes(changes: Any) -> str | None:
    if isinstance(changes, Mapping):
        for field in ("status", "state", "workflowState"):
            value = changes.get(field)
            status = _status_value_from_change(value)
            if status:
                return status
    elif isinstance(changes, list):
        for change in changes:
            if not isinstance(change, Mapping):
                continue
            field = change.get("field") or change.get("name") or change.get("fieldName")
            if _normalize_text(field) not in STATUS_FIELDS:
                continue
            status = _status_value_from_change(change)
            if status:
                return status
    return None


def _status_value_from_change(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("to", "new", "after", "current", "value", "name"):
            status = _string_or_name(value.get(key))
            if status:
                return status
    return _string_or_name(value)


def _first_string(mapping: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = _string_or_name(mapping.get(key))
        if value:
            return value.strip()
    return None


def _string_or_name(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    if isinstance(value, Mapping):
        name = value.get("name") or value.get("title")
        if isinstance(name, str):
            stripped = name.strip()
            return stripped or None
    return None


def _normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    normalized = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    normalized = re.sub(r"[^a-zA-Z0-9]+", " ", normalized)
    return " ".join(normalized.lower().split())


def _normalize_marker(value: Any) -> str:
    return _normalize_text(value).replace(" ", "")


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        json.dump(update, sys.stdout)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
