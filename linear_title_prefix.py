"""Build Linear issue-title updates for research status changes.

The module is intentionally side-effect free: callers pass a webhook or
automation payload to ``build_issue_title_update`` and execute the returned
action with their Linear client if one is produced.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow state", "workflow status"}
_STATUS_TRIGGER_VALUES = {
    "status changed",
    "status updated",
    "state changed",
    "state updated",
    "workflowstate changed",
    "workflowstate updated",
    "workflow state changed",
    "workflow state updated",
    "workflow status changed",
    "workflow status updated",
}
_UPDATE_EVENT_VALUES = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an update action when an issue enters the To Research status."""
    if not isinstance(event, Mapping):
        return None

    payload = _payload(event)
    if not _is_status_change_event(payload):
        return None

    new_status = _new_status(payload)
    if _normalize(new_status) != TARGET_STATUS:
        return None

    issue_id = _first_text(payload, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_text(payload, ("title", "name"))
    if not issue_id or not title or _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _payload(event: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten common Linear webhook and Cursor automation payload shapes."""
    flattened: dict[str, Any] = {}

    for key in ("triggerContext", "data", "issue"):
        value = event.get(key)
        if isinstance(value, Mapping):
            flattened.update(_payload(value))

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            flattened.update(_payload(issue))

    flattened.update(event)
    return flattened


def _is_status_change_event(payload: Mapping[str, Any]) -> bool:
    event_values = _normalized_event_values(payload)
    if event_values & _STATUS_TRIGGER_VALUES:
        return True

    if event_values & _UPDATE_EVENT_VALUES:
        return _mentions_status_field(payload)

    return False


def _normalized_event_values(payload: Mapping[str, Any]) -> set[str]:
    values: set[str] = set()
    for key in ("trigger", "webhookType", "action", "type"):
        value = payload.get(key)
        if isinstance(value, str):
            normalized = _normalize(value)
            if normalized:
                values.add(normalized)
    return values


def _mentions_status_field(payload: Mapping[str, Any]) -> bool:
    for field in _iter_updated_fields(payload):
        if _normalize_field_name(field) in _STATUS_FIELD_NAMES:
            return True

    for change in _iter_changes(payload):
        if not isinstance(change, Mapping):
            continue
        field = _first_text(change, ("field", "fieldName", "name"))
        if _normalize_field_name(field) in _STATUS_FIELD_NAMES:
            return True

    return False


def _new_status(payload: Mapping[str, Any]) -> str | None:
    direct = _first_text(
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
    if direct:
        return direct

    for change in _iter_changes(payload):
        if not isinstance(change, Mapping):
            continue
        field = _first_text(change, ("field", "fieldName", "name"))
        if _normalize_field_name(field) not in _STATUS_FIELD_NAMES:
            continue
        changed_value = _value_name(
            change.get("newValue")
            or change.get("new_value")
            or change.get("to")
            or change.get("after")
        )
        if changed_value:
            return changed_value

    for key in ("workflowState", "state", "status"):
        value = _value_name(payload.get(key))
        if value:
            return value

    return None


def _iter_updated_fields(payload: Mapping[str, Any]) -> Iterable[Any]:
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        value = payload.get(key)
        if isinstance(value, (list, tuple, set)):
            yield from value
        elif value:
            yield value


def _iter_changes(payload: Mapping[str, Any]) -> Iterable[Any]:
    for key in ("changes", "updatedFields", "updated_fields"):
        value = payload.get(key)
        if isinstance(value, Mapping):
            yield from value.values()
        elif isinstance(value, (list, tuple)):
            yield from value


def _first_text(payload: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for key in keys:
        value = payload.get(key)
        text = _value_name(value)
        if text:
            return text.strip()
    return None


def _value_name(value: Any) -> str | None:
    if isinstance(value, str):
        text = value.strip()
        return text or None
    if isinstance(value, Mapping):
        return _first_text(value, ("name", "title", "identifier", "id"))
    return None


def _has_prefix(title: str) -> bool:
    return title.lstrip().lower().startswith(PREFIX.lower())


def _normalize(value: str | None) -> str:
    if not value:
        return ""
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    spaced = re.sub(r"[_\-/]+", " ", spaced)
    return re.sub(r"\s+", " ", spaced).strip().lower()


def _normalize_field_name(value: Any) -> str:
    return _normalize(_value_name(value))


def main() -> None:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update:
        print(json.dumps(update))


if __name__ == "__main__":
    main()
