"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {
    "status",
    "statusid",
    "state",
    "stateid",
    "workflowstate",
    "workflowstateid",
    "workflowstatus",
    "workflowstatusid",
}
TRIGGER_FIELDS = ("trigger", "webhookType", "action", "type")
ISSUE_ID_FIELDS = ("issueId", "issue_id", "identifier", "key", "id")
TITLE_FIELDS = ("title", "name")
NEW_STATUS_FIELDS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "newWorkflowState",
    "new_workflow_state",
    "status",
    "state",
    "workflowState",
    "workflow_state",
)


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update action when an issue moves to "to research"."""

    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_change_event(contexts):
        return None

    status = _new_status(contexts)
    if _normalize(status) != TARGET_STATUS:
        return None

    issue_id = _first_string(contexts, ISSUE_ID_FIELDS)
    title = _first_string(contexts, TITLE_FIELDS)
    if not issue_id or not title:
        return None

    title = title.strip()
    if not title or _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return payload sections in precedence order for metadata and issue data."""

    trigger_context = _mapping_at(event, "triggerContext")
    data = _mapping_at(event, "data")
    issue = _mapping_at(event, "issue")
    data_issue = _mapping_at(data, "issue") if data else None

    contexts: list[Mapping[str, Any]] = []
    for item in (trigger_context, data_issue, issue, data, event):
        if item and item not in contexts:
            contexts.append(item)
    return contexts


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    values = [
        str(context[field])
        for context in contexts
        for field in TRIGGER_FIELDS
        if isinstance(context.get(field), str)
    ]

    if any(_is_direct_status_change(value) for value in values):
        return True

    if any(_normalize(value) in {"update", "updated", "issue updated", "updated issue"} for value in values):
        return _updated_fields_include_status(contexts)

    return _updated_fields_include_status(contexts)


def _is_direct_status_change(value: str) -> bool:
    normalized = _normalize(value)
    return normalized in {
        "status changed",
        "status change",
        "state changed",
        "state change",
        "workflow state changed",
        "workflow state change",
    }


def _updated_fields_include_status(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            fields = context.get(key)
            if _field_collection_has_status(fields):
                return True

        for key in ("changes", "updatedFrom", "updated_from"):
            changes = context.get(key)
            if isinstance(changes, Mapping) and any(_is_status_field(field) for field in changes):
                return True

    return False


def _field_collection_has_status(fields: Any) -> bool:
    if isinstance(fields, str):
        return _is_status_field(fields)
    if isinstance(fields, Mapping):
        return any(_is_status_field(field) for field in fields)
    if isinstance(fields, list | tuple | set):
        return any(_field_collection_has_status(field) for field in fields)
    return False


def _is_status_field(field: Any) -> bool:
    return _normalize_key(field) in STATUS_FIELDS


def _new_status(contexts: list[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        for key in NEW_STATUS_FIELDS:
            value = _status_value(context.get(key))
            if value:
                return value

    for context in contexts:
        for key in ("changes", "updatedFrom", "updated_from"):
            status = _status_from_change_mapping(context.get(key))
            if status:
                return status

    return None


def _status_from_change_mapping(changes: Any) -> str | None:
    if not isinstance(changes, Mapping):
        return None

    for field, value in changes.items():
        if not _is_status_field(field):
            continue

        if isinstance(value, Mapping):
            for key in ("to", "new", "after", "newValue", "new_value", "value", "name"):
                status = _status_value(value.get(key))
                if status:
                    return status
        else:
            status = _status_value(value)
            if status:
                return status

    return None


def _status_value(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        for key in ("name", "title", "value", "id"):
            status = _status_value(value.get(key))
            if status:
                return status
    return None


def _first_string(contexts: list[Mapping[str, Any]], fields: tuple[str, ...]) -> str | None:
    for context in contexts:
        for field in fields:
            value = context.get(field)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def _mapping_at(mapping: Mapping[str, Any], key: str) -> Mapping[str, Any] | None:
    value = mapping.get(key)
    return value if isinstance(value, Mapping) else None


def _normalize(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    cleaned = re.sub(r"[^A-Za-z0-9]+", " ", spaced)
    return " ".join(cleaned.lower().split())


def _normalize_key(value: Any) -> str:
    return _normalize(str(value)).replace(" ", "")


def main() -> int:
    """Read a JSON event from stdin and print the title update action, if any."""

    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    json.dump(build_issue_title_update(event), sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
