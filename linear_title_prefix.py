"""Build Linear issue title update actions for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflowstatus"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to To Research."""
    if not isinstance(event, Mapping):
        return None

    payload = _payload_from_event(event)
    if not _is_status_change_event(payload):
        return None

    status = _extract_new_status(payload)
    if _normalize_text(status) != _normalize_text(RESEARCH_STATUS):
        return None

    issue = _issue_from_payload(payload)
    issue_id = _clean_string(_first_value(issue, ("issueId", "issue_id", "identifier", "key", "id")))
    title = _clean_string(_first_value(issue, ("title", "name")))
    if not issue_id or not title:
        return None

    if title.lower().startswith(TITLE_PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _payload_from_event(event: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten common Cursor automation and Linear webhook wrappers."""
    payload: dict[str, Any] = {}

    automation_context = _mapping_at(event, "automation_trigger_info", "triggerContext")
    trigger_context = _mapping_at(event, "triggerContext")
    data = _mapping_at(event, "data")
    issue = _mapping_at(data, "issue") if data else {}

    for candidate in (issue, data, automation_context, trigger_context, event):
        payload.update(candidate)

    if issue:
        payload["issue"] = dict(issue)
    if data:
        payload["data"] = dict(data)

    return payload


def _issue_from_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    issue: dict[str, Any] = {}
    data = _mapping_at(payload, "data")
    nested_issue = _mapping_at(data, "issue") if data else _mapping_at(payload, "issue")

    for candidate in (nested_issue, payload):
        issue.update(candidate)

    return issue


def _is_status_change_event(payload: Mapping[str, Any]) -> bool:
    event_names = [
        _normalize_event_name(value)
        for key in ("trigger", "webhookType", "action", "type")
        for value in _values_for_key(payload, key)
    ]

    if any(name in {"statuschanged", "statechanged", "workflowstatechanged"} for name in event_names):
        return True

    if any(name in {"update", "updated", "issueupdated", "updatedissue"} for name in event_names):
        return _status_field_changed(payload)

    return False


def _status_field_changed(payload: Mapping[str, Any]) -> bool:
    updated_fields = payload.get("updatedFields")
    if _contains_status_field(updated_fields):
        return True

    changes = payload.get("changes")
    if isinstance(changes, Mapping):
        return any(_normalize_field_name(key) in STATUS_FIELDS for key in changes)

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_field_name(value) in STATUS_FIELDS

    if isinstance(value, Mapping):
        return any(_contains_status_field(key) or _contains_status_field(item) for key, item in value.items())

    if isinstance(value, list | tuple | set):
        return any(_contains_status_field(item) for item in value)

    return False


def _extract_new_status(payload: Mapping[str, Any]) -> str | None:
    for key in ("newStatus", "new_status", "newState", "new_state", "newWorkflowState", "new_workflow_state"):
        value = _first_value(payload, (key,))
        status = _status_name(value)
        if status:
            return status

    status_from_changes = _status_from_changes(payload.get("changes"))
    if status_from_changes:
        return status_from_changes

    for key in ("status", "state", "workflowState", "workflowStatus"):
        value = _first_value(payload, (key,))
        status = _status_name(value)
        if status:
            return status

    return None


def _status_from_changes(changes: Any) -> str | None:
    if not isinstance(changes, Mapping):
        return None

    for key, value in changes.items():
        if _normalize_field_name(key) not in STATUS_FIELDS:
            continue

        if isinstance(value, Mapping):
            for changed_key in ("to", "toValue", "newValue", "after", "current"):
                status = _status_name(value.get(changed_key))
                if status:
                    return status

        status = _status_name(value)
        if status:
            return status

    return None


def _status_name(value: Any) -> str | None:
    if isinstance(value, str):
        return value

    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            status = _status_name(value.get(key))
            if status:
                return status

    return None


def _first_value(mapping: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in mapping:
            return mapping[key]
    return None


def _values_for_key(mapping: Mapping[str, Any], key: str) -> list[Any]:
    values: list[Any] = []
    if key in mapping:
        values.append(mapping[key])

    data = _mapping_at(mapping, "data")
    if data and key in data:
        values.append(data[key])

    return values


def _mapping_at(mapping: Mapping[str, Any] | None, *keys: str) -> dict[str, Any]:
    current: Any = mapping
    for key in keys:
        if not isinstance(current, Mapping):
            return {}
        current = current.get(key)
    return dict(current) if isinstance(current, Mapping) else {}


def _clean_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    value = value.strip()
    return value or None


def _normalize_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    return re.sub(r"[^a-z0-9]+", " ", spaced.lower()).strip()


def _normalize_event_name(value: Any) -> str | None:
    normalized = _normalize_text(value)
    return normalized.replace(" ", "") if normalized else None


def _normalize_field_name(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    return re.sub(r"[^a-z0-9]+", "", value.lower())


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        json.dump(action, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
