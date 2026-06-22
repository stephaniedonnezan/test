"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"

_STATUS_FIELDS = {"status", "state", "workflow state", "workflow status"}
_DIRECT_STATUS_TRIGGERS = {
    "status changed",
    "status change",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
}
_GENERIC_UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear issue-title update action when an issue enters research."""
    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    status = _destination_status(event)
    if _normalize_text(status) != _normalize_text(TARGET_STATUS):
        return None

    issue = _issue_from_event(event)
    if issue is None:
        return None

    issue_id, title = issue
    if title.casefold().startswith(PREFIX.casefold()):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    trigger_values = []
    for payload in _metadata_payloads(event):
        for key in ("trigger", "action", "type", "webhookType", "webhook_type"):
            value = payload.get(key)
            if isinstance(value, str):
                trigger_values.append(_normalize_text(value))

    if any(value in _DIRECT_STATUS_TRIGGERS for value in trigger_values):
        return True

    if any(value in _GENERIC_UPDATE_TRIGGERS for value in trigger_values):
        return _status_field_changed(event)

    return False


def _destination_status(event: Mapping[str, Any]) -> str | None:
    for payload in _metadata_payloads(event):
        for key in (
            "newStatus",
            "new_status",
            "statusAfter",
            "status_after",
            "afterStatus",
            "after_status",
            "toStatus",
            "to_status",
            "statusTo",
            "status_to",
            "newState",
            "new_state",
            "stateAfter",
            "state_after",
            "toState",
            "to_state",
            "newWorkflowState",
            "new_workflow_state",
            "workflowStateAfter",
            "workflow_state_after",
            "toWorkflowState",
            "to_workflow_state",
        ):
            status = _status_value(payload.get(key))
            if status:
                return status

    changed_status = _status_from_changes(event)
    if changed_status:
        return changed_status

    for payload in _metadata_payloads(event):
        status = _status_value(payload.get("status"))
        if status:
            return status

        for key in ("state", "workflowState", "workflow_state"):
            status = _status_value(payload.get(key))
            if status:
                return status

    return None


def _status_from_changes(event: Mapping[str, Any]) -> str | None:
    for payload in _metadata_payloads(event):
        changes = payload.get("changes")
        if not isinstance(changes, Mapping):
            continue

        for key, value in changes.items():
            if _normalize_text(str(key)) not in _STATUS_FIELDS:
                continue

            status = _changed_value(value)
            if status:
                return status

    return None


def _changed_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in (
            "to",
            "new",
            "after",
            "current",
            "newValue",
            "new_value",
            "toValue",
            "to_value",
        ):
            status = _status_value(value.get(key))
            if status:
                return status
        return _status_value(value)

    if isinstance(value, list) and len(value) >= 2:
        return _status_value(value[1])

    return _status_value(value)


def _status_field_changed(event: Mapping[str, Any]) -> bool:
    for payload in _metadata_payloads(event):
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            fields = payload.get(key)
            if _contains_status_field(fields):
                return True

        changes = payload.get("changes")
        if isinstance(changes, Mapping):
            if any(_normalize_text(str(key)) in _STATUS_FIELDS for key in changes):
                return True
        elif _contains_status_field(changes):
            return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_text(value) in _STATUS_FIELDS

    if isinstance(value, Mapping):
        for key in ("field", "name", "key", "path"):
            if _contains_status_field(value.get(key)):
                return True
        return any(_contains_status_field(key) for key in value)

    if isinstance(value, Iterable):
        return any(_contains_status_field(item) for item in value)

    return False


def _issue_from_event(event: Mapping[str, Any]) -> tuple[str, str] | None:
    for payload in _issue_payloads(event):
        issue_id = _first_text(
            payload,
            ("issueId", "issue_id", "identifier", "key", "id"),
        )
        title = _first_text(payload, ("title",))
        if issue_id and title:
            return issue_id, title

    return None


def _metadata_payloads(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    payloads: list[Mapping[str, Any]] = []

    def add(payload: Any) -> None:
        if isinstance(payload, Mapping) and payload not in payloads:
            payloads.append(payload)

    add(event)
    for wrapper_key in (
        "automation_trigger_info",
        "automationTriggerInfo",
        "triggerInfo",
        "trigger_info",
    ):
        wrapper = event.get(wrapper_key)
        add(wrapper)
        if isinstance(wrapper, Mapping):
            add(wrapper.get("triggerContext"))
            add(wrapper.get("trigger_context"))

    add(event.get("triggerContext"))
    add(event.get("trigger_context"))
    add(event.get("issue"))

    data = event.get("data")
    add(data)
    if isinstance(data, Mapping):
        add(data.get("issue"))

    return payloads


def _issue_payloads(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    payloads: list[Mapping[str, Any]] = []

    def add(payload: Any) -> None:
        if isinstance(payload, Mapping) and payload not in payloads:
            payloads.append(payload)

    for payload in _metadata_payloads(event):
        add(payload)
        add(payload.get("issue"))
        data = payload.get("data")
        add(data)
        if isinstance(data, Mapping):
            add(data.get("issue"))

    return payloads


def _first_text(payload: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str):
            value = value.strip()
            if value:
                return value
    return None


def _status_value(value: Any) -> str | None:
    if isinstance(value, str):
        value = value.strip()
        return value or None

    if isinstance(value, Mapping):
        return _first_text(value, ("name", "title", "label"))

    return None


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""

    value = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    value = re.sub(r"[^A-Za-z0-9]+", " ", value)
    return " ".join(value.casefold().split())


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, indent=2, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
