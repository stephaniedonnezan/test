"""Build Linear issue-title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflow state", "workflowstate"}
DIRECT_STATUS_CHANGE_EVENTS = {
    "status changed",
    "state changed",
    "workflow state changed",
    "workflowstate changed",
}
GENERIC_UPDATE_EVENTS = {"update", "updated", "issue update", "issue updated", "updated issue"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title-update action when an issue moves to research."""

    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_change_event(contexts):
        return None

    new_status = _new_status(contexts)
    if _normalize_label(new_status) != TARGET_STATUS:
        return None

    issue_id = _issue_id(contexts)
    title = _issue_title(contexts)
    if not issue_id or not title:
        return None

    title = title.strip()
    if title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return payload fragments from most issue-specific to most generic."""

    contexts: list[Mapping[str, Any]] = []

    trigger_context = _mapping(event.get("triggerContext"))
    data = _mapping(event.get("data"))
    issue = _mapping(event.get("issue"))
    if not issue and data:
        issue = _mapping(data.get("issue"))

    for candidate in (trigger_context, issue, data, event):
        if candidate and candidate not in contexts:
            contexts.append(candidate)

    return contexts


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    event_values = []
    for context in contexts:
        for key in ("trigger", "action", "type", "webhookType", "eventType"):
            if key in context:
                event_values.append(_normalize_label(context.get(key)))

    if any(value in DIRECT_STATUS_CHANGE_EVENTS for value in event_values):
        return True

    if any(value in GENERIC_UPDATE_EVENTS for value in event_values):
        return _has_status_change_metadata(contexts)

    return _has_status_change_metadata(contexts) and any(value == "issue" for value in event_values)


def _has_status_change_metadata(contexts: list[Mapping[str, Any]]) -> bool:
    return any(_updated_fields_include_status(context) or _changes_include_status(context) for context in contexts)


def _updated_fields_include_status(context: Mapping[str, Any]) -> bool:
    updated_fields = context.get("updatedFields") or context.get("updated_fields") or context.get("changedFields")
    if isinstance(updated_fields, str):
        fields = [updated_fields]
    elif isinstance(updated_fields, (list, tuple, set)):
        fields = list(updated_fields)
    else:
        return False

    return any(_normalize_label(field) in STATUS_FIELDS for field in fields)


def _changes_include_status(context: Mapping[str, Any]) -> bool:
    changes = context.get("changes") or context.get("change")
    if isinstance(changes, Mapping):
        return any(_normalize_label(field) in STATUS_FIELDS for field in changes)

    if isinstance(changes, (list, tuple)):
        for change in changes:
            change_map = _mapping(change)
            field = (
                change_map.get("field")
                or change_map.get("fieldName")
                or change_map.get("name")
                or change_map.get("key")
            )
            if _normalize_label(field) in STATUS_FIELDS:
                return True

    return False


def _new_status(contexts: list[Mapping[str, Any]]) -> Any:
    for context in contexts:
        status = _status_from_explicit_keys(context)
        if status is not None:
            return status

    for context in contexts:
        status = _status_from_changes(context)
        if status is not None:
            return status

    for context in contexts:
        for key in ("status", "state", "workflowState", "workflow_state"):
            status = _status_value(context.get(key))
            if status is not None:
                return status

    return None


def _status_from_explicit_keys(context: Mapping[str, Any]) -> Any:
    for key in (
        "newStatus",
        "new_status",
        "toStatus",
        "to_status",
        "newState",
        "new_state",
        "toState",
        "to_state",
        "newWorkflowState",
        "new_workflow_state",
    ):
        status = _status_value(context.get(key))
        if status is not None:
            return status

    return None


def _status_from_changes(context: Mapping[str, Any]) -> Any:
    changes = context.get("changes") or context.get("change")
    if isinstance(changes, Mapping):
        for field, value in changes.items():
            if _normalize_label(field) in STATUS_FIELDS:
                return _changed_to_value(value)

    if isinstance(changes, (list, tuple)):
        for change in changes:
            change_map = _mapping(change)
            field = (
                change_map.get("field")
                or change_map.get("fieldName")
                or change_map.get("name")
                or change_map.get("key")
            )
            if _normalize_label(field) in STATUS_FIELDS:
                return _changed_to_value(change_map)

    return None


def _changed_to_value(value: Any) -> Any:
    value_map = _mapping(value)
    if value_map:
        for key in ("to", "new", "after", "newValue", "new_value", "value", "name"):
            status = _status_value(value_map.get(key))
            if status is not None:
                return status

    return _status_value(value)


def _issue_id(contexts: list[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        keys = ["issueId", "issue_id", "identifier", "key"]
        if "automationId" not in context:
            keys.append("id")

        for key in keys:
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value

    return None


def _issue_title(contexts: list[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        value = context.get("title")
        if isinstance(value, str) and value.strip():
            return value

    return None


def _status_value(value: Any) -> Any:
    value_map = _mapping(value)
    if value_map:
        for key in ("name", "title", "label", "key", "id"):
            nested = value_map.get(key)
            if isinstance(nested, str) and nested.strip():
                return nested
        return None

    if isinstance(value, str) and value.strip():
        return value

    return None


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _normalize_label(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value.strip())
    normalized = re.sub(r"[^A-Za-z0-9]+", " ", spaced).lower()
    return " ".join(normalized.split())


def main() -> int:
    payload = json.load(sys.stdin)
    update = build_issue_title_update(payload)
    if update is None:
        return 0

    print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
