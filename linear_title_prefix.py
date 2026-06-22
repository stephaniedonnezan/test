"""Build Linear issue title update actions for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
ACTION = "update_issue_title"

_STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflowstatus"}
_DIRECT_STATUS_TRIGGERS = {
    "statuschanged",
    "statechanged",
    "workflowstatechanged",
    "workflowstatuschanged",
}
_GENERIC_UPDATE_TRIGGERS = {"issueupdated", "updatedissue", "update", "updated"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to To Research."""

    if not isinstance(event, Mapping):
        return None

    payload = _payload(event)
    if not _is_status_change(payload):
        return None

    new_status = _extract_new_status(payload)
    if _normalize_text(new_status) != _normalize_text(TARGET_STATUS):
        return None

    issue = _issue(payload)
    issue_id = _clean_text(_first_value(issue, ("issueId", "issue_id", "id", "identifier", "key")))
    title = _clean_text(_first_value(issue, ("title", "name")))
    if not issue_id or not title:
        return None

    if title.lower().startswith(PREFIX.lower()):
        return None

    return {"action": ACTION, "issueId": issue_id, "title": f"{PREFIX}: {title}"}


def _payload(event: Mapping[str, Any]) -> Mapping[str, Any]:
    """Prefer Cursor trigger context, while preserving top-level Linear metadata."""

    for key in ("automation_trigger_info", "automationTriggerInfo"):
        nested = event.get(key)
        if isinstance(nested, Mapping):
            trigger_context = nested.get("triggerContext") or nested.get("trigger_context")
            if isinstance(trigger_context, Mapping):
                return {**nested, **trigger_context}

    trigger_context = event.get("triggerContext") or event.get("trigger_context")
    if isinstance(trigger_context, Mapping):
        return {**event, **trigger_context}

    return event


def _issue(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    issue = _deep_get(payload, ("data", "issue"))
    if isinstance(issue, Mapping):
        return {**payload, **issue}

    data = payload.get("data")
    if isinstance(data, Mapping):
        return {**payload, **data}

    return payload


def _is_status_change(payload: Mapping[str, Any]) -> bool:
    trigger_values = _trigger_values(payload)
    if any(value in _DIRECT_STATUS_TRIGGERS for value in trigger_values):
        return True

    if any(value in _GENERIC_UPDATE_TRIGGERS for value in trigger_values):
        return _has_status_field_change(payload)

    return False


def _trigger_values(payload: Mapping[str, Any]) -> set[str]:
    values: set[str] = set()
    for key in ("trigger", "webhookType", "webhook_type", "action", "type"):
        raw = payload.get(key)
        if isinstance(raw, str):
            values.add(_normalize_text(raw))

    data = payload.get("data")
    if isinstance(data, Mapping):
        for key in ("trigger", "webhookType", "webhook_type", "action", "type"):
            raw = data.get(key)
            if isinstance(raw, str):
                values.add(_normalize_text(raw))

    return values


def _has_status_field_change(payload: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        if _contains_status_field(payload.get(key)):
            return True

    changes = payload.get("changes") or payload.get("updatedFrom")
    if isinstance(changes, Mapping):
        return any(_is_status_field_name(key) for key in changes)

    data = payload.get("data")
    if isinstance(data, Mapping):
        return _has_status_field_change(data)

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field_name(value)

    if isinstance(value, Iterable) and not isinstance(value, (str, bytes, Mapping)):
        return any(_contains_status_field(item) for item in value)

    if isinstance(value, Mapping):
        return any(_is_status_field_name(key) for key in value)

    return False


def _is_status_field_name(name: Any) -> bool:
    return isinstance(name, str) and _normalize_text(name) in _STATUS_FIELD_NAMES


def _extract_new_status(payload: Mapping[str, Any]) -> str | None:
    for key in (
        "newStatus",
        "new_status",
        "statusName",
        "status_name",
        "newState",
        "new_state",
        "workflowState",
        "workflow_state",
    ):
        status = _status_name(payload.get(key))
        if status:
            return status

    changed_status = _status_from_changes(payload.get("changes"))
    if changed_status:
        return changed_status

    data = payload.get("data")
    if isinstance(data, Mapping):
        nested_status = _extract_new_status(data)
        if nested_status:
            return nested_status

    issue = _issue(payload)
    for key in ("status", "state", "workflowState", "workflow_state"):
        status = _status_name(issue.get(key))
        if status:
            return status

    return None


def _status_from_changes(changes: Any) -> str | None:
    if not isinstance(changes, Mapping):
        return None

    for key, change in changes.items():
        if not _is_status_field_name(key):
            continue

        if isinstance(change, Mapping):
            for value_key in ("to", "newValue", "new_value", "after", "current"):
                status = _status_name(change.get(value_key))
                if status:
                    return status
        else:
            status = _status_name(change)
            if status:
                return status

    return None


def _status_name(value: Any) -> str | None:
    if isinstance(value, str):
        return value

    if isinstance(value, Mapping):
        for key in ("name", "title", "status", "state"):
            status = _status_name(value.get(key))
            if status:
                return status

    return None


def _first_value(mapping: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = mapping.get(key)
        if value is not None:
            return value
    return None


def _deep_get(mapping: Mapping[str, Any], path: tuple[str, ...]) -> Any:
    current: Any = mapping
    for key in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current


def _clean_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    stripped = value.strip()
    return stripped or None


def _normalize_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    words = re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)|\d+", value)
    return "".join(word.lower() for word in words)


def main() -> int:
    """Read a JSON event from stdin and print the title update action or null."""

    event = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(event), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
