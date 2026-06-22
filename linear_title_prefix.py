"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {
    "status",
    "status id",
    "state",
    "state id",
    "workflow status",
    "workflow status id",
    "workflow state",
    "workflow state id",
}
STATUS_CHANGE_EVENTS = {
    "status changed",
    "state changed",
    "workflow status changed",
    "workflow state changed",
}
GENERIC_UPDATE_EVENTS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title-update action when a Linear issue moves to research."""

    if not isinstance(event, Mapping):
        return None

    contexts = _payload_contexts(event)
    if not _is_status_change_event(contexts):
        return None

    status = _extract_new_status(contexts)
    if _normalize_text(status) != TARGET_STATUS:
        return None

    issue_id = _extract_issue_id(contexts)
    title = _extract_title(contexts)
    if not issue_id or not title:
        return None
    if _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _payload_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return relevant payload maps, from most issue-specific to broadest."""

    contexts: list[Mapping[str, Any]] = []

    automation_info = _mapping_value(event, "automation_trigger_info", "automationTriggerInfo")
    if automation_info:
        _append_mapping(contexts, _mapping_value(automation_info, "triggerContext"))

    _append_mapping(contexts, _mapping_value(event, "triggerContext"))

    data = _mapping_value(event, "data")
    if data:
        _append_mapping(contexts, _mapping_value(data, "issue"))
        _append_mapping(contexts, data)

    _append_mapping(contexts, _mapping_value(event, "issue"))
    _append_mapping(contexts, event)
    return contexts


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    has_update_event = False
    has_status_change_field = False

    for context in contexts:
        for key in ("trigger", "action", "type", "webhookType", "webhook_type", "event"):
            event_name = _normalize_text(context.get(key))
            if event_name in STATUS_CHANGE_EVENTS:
                return True
            if event_name in GENERIC_UPDATE_EVENTS:
                has_update_event = True

        if _has_status_change_field(context):
            has_status_change_field = True

    return has_update_event and has_status_change_field


def _has_status_change_field(context: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        if _contains_status_field(context.get(key)):
            return True

    changes = context.get("changes") or context.get("changed")
    if isinstance(changes, Mapping):
        return any(_is_status_field_name(key) for key in changes)

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field_name(value)
    if isinstance(value, Mapping):
        return any(_is_status_field_name(key) for key in value) or any(
            _contains_status_field(nested) for nested in value.values()
        )
    if isinstance(value, Iterable):
        return any(_contains_status_field(item) for item in value)
    return False


def _is_status_field_name(value: Any) -> bool:
    return _normalize_text(value) in STATUS_FIELD_NAMES


def _extract_new_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    context_list = list(contexts)

    for context in context_list:
        status = _first_scalar(
            context,
            (
                "newStatus",
                "new_status",
                "statusName",
                "status_name",
                "stateName",
                "state_name",
                "workflowStatusName",
                "workflow_status_name",
                "workflowStateName",
                "workflow_state_name",
            ),
        )
        if status:
            return status

    for context in context_list:
        status = _status_from_changes(context)
        if status:
            return status

    for context in context_list:
        status = _first_scalar(
            context,
            (
                "status",
                "state",
                "workflowStatus",
                "workflow_status",
                "workflowState",
                "workflow_state",
            ),
        )
        if status:
            return status

    return None


def _status_from_changes(context: Mapping[str, Any]) -> str | None:
    for key in ("changes", "changed"):
        changes = context.get(key)
        if not isinstance(changes, Mapping):
            continue

        for field, change in changes.items():
            if not _is_status_field_name(field):
                continue
            status = _value_from_change(change)
            if status:
                return status

    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        field_change = context.get(key)
        if isinstance(field_change, Mapping):
            for field, change in field_change.items():
                if not _is_status_field_name(field):
                    continue
                status = _value_from_change(change)
                if status:
                    return status

        status = _value_from_change(field_change)
        if status:
            return status

    return None


def _value_from_change(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, Mapping):
        for key in (
            "to",
            "new",
            "newValue",
            "new_value",
            "after",
            "value",
            "name",
            "label",
        ):
            scalar = _scalar_string(value.get(key))
            if scalar:
                return scalar
        return _first_scalar(value, ("status", "state", "workflowStatus", "workflowState"))
    if isinstance(value, Iterable):
        for item in value:
            status = _value_from_change(item)
            if status and not _is_status_field_name(status):
                return status
    return None


def _extract_issue_id(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        issue_id = _first_scalar(
            context,
            ("issueId", "issue_id", "identifier", "key", "id"),
        )
        if issue_id:
            return issue_id
    return None


def _extract_title(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        title = _first_scalar(context, ("title",))
        if title:
            return title
    return None


def _first_scalar(context: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for key in keys:
        value = _scalar_string(context.get(key))
        if value:
            return value
    return None


def _scalar_string(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, Mapping):
        return _first_scalar(value, ("name", "label", "title"))
    return None


def _mapping_value(context: Mapping[str, Any], *keys: str) -> Mapping[str, Any] | None:
    for key in keys:
        value = context.get(key)
        if isinstance(value, Mapping):
            return value
    return None


def _append_mapping(
    contexts: list[Mapping[str, Any]], value: Mapping[str, Any] | None
) -> None:
    if value and not any(value is existing for existing in contexts):
        contexts.append(value)


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def _normalize_text(value: Any) -> str:
    scalar = _scalar_string(value)
    if not scalar:
        return ""
    with_spaces = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", scalar)
    with_spaces = re.sub(r"[^A-Za-z0-9]+", " ", with_spaces)
    return re.sub(r"\s+", " ", with_spaces).strip().lower()


def main() -> int:
    payload = json.load(sys.stdin)
    result = build_issue_title_update(payload)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
