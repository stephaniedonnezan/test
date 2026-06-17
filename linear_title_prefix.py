"""Build Linear issue title update actions for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow status", "workflow_status"}
DIRECT_STATUS_TRIGGERS = {"status changed", "status change", "statuschanged"}
GENERIC_UPDATE_TRIGGERS = {
    "issue updated",
    "updated issue",
    "update",
    "updated",
    "issue update",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue title update action for a move to the research status.

    The Cursor automation trigger can be flat under ``triggerContext`` while
    Linear webhooks commonly nest issue data under ``data.issue``. This helper
    accepts both shapes and returns a small action object that an automation
    runner can apply to Linear.
    """

    if not isinstance(event, Mapping):
        return None

    payload = _merge_payload(event)
    if not _is_status_change_event(payload):
        return None

    status = _extract_new_status(payload)
    if _normalize_text(status) != TARGET_STATUS:
        return None

    issue_id = _extract_issue_id(payload)
    title = _clean_string(payload.get("title"))
    if not issue_id or not title:
        return None

    if _has_prefix(title):
        prefixed_title = title
    else:
        prefixed_title = f"{PREFIX}: {title}"

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": prefixed_title,
    }


def _merge_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten known wrapper objects while preserving outer trigger metadata."""

    merged: dict[str, Any] = {}

    trigger_context = _mapping_value(event.get("triggerContext"))
    data = _mapping_value(event.get("data"))
    issue = _mapping_value(data.get("issue")) if data else {}

    for source in (issue, data, trigger_context, event):
        for key, value in source.items():
            if key in {"data", "issue", "triggerContext"}:
                continue
            if value is not None:
                merged[key] = value

    return merged


def _is_status_change_event(payload: Mapping[str, Any]) -> bool:
    trigger_values = [
        payload.get("trigger"),
        payload.get("webhookType"),
        payload.get("action"),
        payload.get("type"),
    ]

    normalized_triggers = {
        normalized for value in trigger_values if (normalized := _normalize_text(value))
    }

    if any(trigger in DIRECT_STATUS_TRIGGERS for trigger in normalized_triggers):
        return True

    if any(trigger in GENERIC_UPDATE_TRIGGERS for trigger in normalized_triggers):
        return _changed_fields_include_status(payload)

    return False


def _changed_fields_include_status(payload: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "changedFields"):
        fields = payload.get(key)
        if _sequence_mentions_status(fields):
            return True

    changes = payload.get("changes")
    if isinstance(changes, Mapping):
        return any(_normalize_field_name(key) in STATUS_FIELDS for key in changes)

    if isinstance(changes, Sequence) and not isinstance(changes, (str, bytes)):
        for change in changes:
            if isinstance(change, Mapping):
                field = change.get("field") or change.get("name") or change.get("key")
                if _normalize_field_name(field) in STATUS_FIELDS:
                    return True
            elif _normalize_field_name(change) in STATUS_FIELDS:
                return True

    return False


def _extract_new_status(payload: Mapping[str, Any]) -> str | None:
    for key in ("newStatus", "new_status", "statusName", "stateName", "workflowStateName"):
        value = _clean_string(payload.get(key))
        if value:
            return value

    changed_status = _status_from_changes(payload.get("changes"))
    if changed_status:
        return changed_status

    for key in ("status", "state", "workflowState"):
        value = payload.get(key)
        if isinstance(value, Mapping):
            status = _clean_string(value.get("name") or value.get("title"))
        else:
            status = _clean_string(value)
        if status:
            return status

    return None


def _status_from_changes(changes: Any) -> str | None:
    if isinstance(changes, Mapping):
        for field, change in changes.items():
            if _normalize_field_name(field) in STATUS_FIELDS:
                return _new_value_from_change(change)
        return None

    if isinstance(changes, Sequence) and not isinstance(changes, (str, bytes)):
        for change in changes:
            if not isinstance(change, Mapping):
                continue
            field = change.get("field") or change.get("name") or change.get("key")
            if _normalize_field_name(field) in STATUS_FIELDS:
                return _new_value_from_change(change)

    return None


def _new_value_from_change(change: Any) -> str | None:
    if isinstance(change, Mapping):
        for key in ("newValue", "new_value", "to", "after", "new"):
            value = change.get(key)
            if isinstance(value, Mapping):
                status = _clean_string(value.get("name") or value.get("title"))
            else:
                status = _clean_string(value)
            if status:
                return status
    return _clean_string(change)


def _sequence_mentions_status(fields: Any) -> bool:
    if isinstance(fields, Sequence) and not isinstance(fields, (str, bytes)):
        return any(_normalize_field_name(field) in STATUS_FIELDS for field in fields)
    return False


def _extract_issue_id(payload: Mapping[str, Any]) -> str | None:
    for key in ("identifier", "issueId", "issue_id", "key", "id"):
        issue_id = _clean_string(payload.get(key))
        if issue_id:
            return issue_id
    return None


def _has_prefix(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())


def _mapping_value(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _clean_string(value: Any) -> str | None:
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return None


def _normalize_field_name(value: Any) -> str:
    normalized = _normalize_text(value)
    return normalized.replace(" ", "") if normalized == "workflow state" else normalized


def _normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    value = re.sub(r"[_\-\s]+", " ", value)
    return value.strip().casefold()


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is None:
        return 0
    json.dump(update, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
