"""Build Linear issue-title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
ACTION = "update_issue_title"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {"status", "state", "workflow state", "workflowstate"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when an issue moves to To Research.

    The automation trigger can arrive as a flat Cursor ``triggerContext`` event
    or as a nested Linear webhook payload. This function only builds an update
    for status/state changes whose new status normalizes to "to research".
    """

    if not isinstance(event, Mapping):
        return None

    payloads = _payloads(event)
    if not _is_status_change_event(payloads):
        return None

    status = _new_status(payloads)
    if _normalize(status) != TARGET_STATUS:
        return None

    issue_id = _first_string(payloads, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_string(payloads, ("title", "name"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if not title or _has_prefix(title):
        return None

    return {
        "action": ACTION,
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _payloads(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    payloads: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in payloads:
            payloads.append(value)

    add(event)
    trigger_context = event.get("triggerContext")
    add(trigger_context)
    if isinstance(trigger_context, Mapping):
        add(trigger_context.get("data"))
        add(trigger_context.get("issue"))

    data = event.get("data")
    add(data)
    if isinstance(data, Mapping):
        add(data.get("issue"))

    add(event.get("issue"))
    return payloads


def _is_status_change_event(payloads: list[Mapping[str, Any]]) -> bool:
    event_values = _event_values(payloads)
    if any(_is_direct_status_change(value) for value in event_values):
        return True

    if not any(_is_generic_issue_update(value) for value in event_values):
        return False

    return _changed_status_fields(payloads)


def _event_values(payloads: list[Mapping[str, Any]]) -> list[Any]:
    keys = ("trigger", "webhookType", "eventType", "type", "action")
    return [payload[key] for payload in payloads for key in keys if key in payload]


def _is_direct_status_change(value: Any) -> bool:
    normalized = _normalize(value)
    compact = normalized.replace(" ", "")
    return normalized in {
        "status changed",
        "status updated",
        "state changed",
        "state updated",
        "workflow state changed",
        "issue status changed",
        "issue state changed",
    } or compact in {"statuschanged", "statusupdated", "statechanged", "stateupdated"}


def _is_generic_issue_update(value: Any) -> bool:
    normalized = _normalize(value)
    return normalized in {"update", "updated", "issue updated", "updated issue"}


def _changed_status_fields(payloads: list[Mapping[str, Any]]) -> bool:
    for payload in payloads:
        for key in ("updatedFields", "changedFields", "updated_fields", "changed_fields"):
            if _field_list_has_status(payload.get(key)):
                return True

        for key in ("changes", "changed", "updatedFrom", "updated_from"):
            changes = payload.get(key)
            if isinstance(changes, Mapping) and any(_is_status_field(name) for name in changes):
                return True

    return False


def _field_list_has_status(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)

    if isinstance(value, list | tuple | set):
        return any(_field_list_has_status(item) for item in value)

    return False


def _is_status_field(value: Any) -> bool:
    normalized = _normalize(value)
    compact = normalized.replace(" ", "")
    return normalized in _STATUS_FIELD_NAMES or compact in _STATUS_FIELD_NAMES or compact in {
        "statusid",
        "stateid",
        "workflowstateid",
    }


def _new_status(payloads: list[Mapping[str, Any]]) -> Any:
    explicit_keys = (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "newWorkflowState",
        "new_workflow_state",
        "toStatus",
        "to_status",
        "toState",
        "to_state",
        "statusName",
        "stateName",
        "workflowStateName",
    )
    for payload in payloads:
        status = _value_from_keys(payload, explicit_keys)
        if status is not None:
            return status

    changed_status = _status_from_changes(payloads)
    if changed_status is not None:
        return changed_status

    for payload in payloads:
        status = _value_from_keys(payload, ("status", "state", "workflowState", "workflow_state"))
        if status is not None:
            return status

    return None


def _status_from_changes(payloads: list[Mapping[str, Any]]) -> Any:
    for payload in payloads:
        for key in ("changes", "changed"):
            changes = payload.get(key)
            if not isinstance(changes, Mapping):
                continue

            for field, value in changes.items():
                if _is_status_field(field):
                    status = _status_change_value(value)
                    if status is not None:
                        return status

    return None


def _status_change_value(value: Any) -> Any:
    if not isinstance(value, Mapping):
        return value

    for key in ("new", "to", "after", "current", "newValue", "new_value", "value", "name"):
        if key in value:
            nested_value = value[key]
            if isinstance(nested_value, Mapping):
                return _value_from_keys(nested_value, ("name", "title", "label"))
            return nested_value

    return _value_from_keys(value, ("name", "title", "label"))


def _value_from_keys(payload: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key not in payload:
            continue

        value = payload[key]
        if isinstance(value, Mapping):
            nested_value = _value_from_keys(value, ("name", "title", "label"))
            if nested_value is not None:
                return nested_value
        elif value is not None:
            return value

    return None


def _first_string(payloads: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        for payload in payloads:
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _has_prefix(title: str) -> bool:
    return re.match(rf"^\s*{re.escape(PREFIX)}\b", title, flags=re.IGNORECASE) is not None


def _normalize(value: Any) -> str:
    if value is None:
        return ""

    text = str(value).strip()
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
