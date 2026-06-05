"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to To Research."""
    if not isinstance(event, Mapping):
        return None

    context = _event_context(event)
    if not _is_status_change_event(context):
        return None

    new_status = _new_status(context)
    if _normalize_text(new_status) != TARGET_STATUS:
        return None

    issue_id = _first_text(context, ("issueId", "issue_id", "identifier", "key", "uuid", "id"))
    title = _first_text(context, ("title", "name"))
    if not issue_id or not title:
        return None

    if title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def handle_issue_status_changed(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Compatibility wrapper used by some Cursor automation examples."""
    return build_issue_title_update(event)


def _event_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common Cursor/Linear nesting shapes into one lookup context."""
    trigger_context = _mapping_value(event, "triggerContext")
    data = _mapping_value(event, "data")
    data_issue = _mapping_value(data, "issue")
    top_issue = _mapping_value(event, "issue")

    context: dict[str, Any] = {}
    for source in (event, trigger_context, data, top_issue, data_issue):
        if source:
            context.update(source)

    # Preserve nested issue identity/title over webhook/event IDs.
    for issue in (top_issue, data_issue):
        if not issue:
            continue
        for key in ("id", "issueId", "issue_id", "identifier", "key", "uuid", "title", "name"):
            if key in issue:
                context[key] = issue[key]

    return context


def _is_status_change_event(context: Mapping[str, Any]) -> bool:
    trigger_values = [
        _text_value(context.get(key))
        for key in ("trigger", "webhookType", "action", "type")
    ]
    normalized_triggers = {_normalize_identifier(value) for value in trigger_values if value}

    if normalized_triggers & {"statuschanged", "statuschange", "issuestatuschanged"}:
        return True

    update_triggers = {"update", "updated", "issueupdated", "updatedissue"}
    if normalized_triggers & update_triggers:
        return _status_field_changed(context)

    if normalized_triggers:
        return False

    return _status_field_changed(context) and bool(_new_status(context))


def _status_field_changed(context: Mapping[str, Any]) -> bool:
    updated_fields = context.get("updatedFields")
    if isinstance(updated_fields, list | tuple | set):
        if any(_normalize_identifier(field) in STATUS_FIELDS for field in updated_fields):
            return True

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        if any(_normalize_identifier(field) in STATUS_FIELDS for field in changes):
            return True
    elif isinstance(changes, list | tuple):
        for change in changes:
            if isinstance(change, Mapping):
                field_name = _first_text(change, ("field", "fieldName", "name", "key"))
                if _normalize_identifier(field_name) in STATUS_FIELDS:
                    return True
            elif _normalize_identifier(change) in STATUS_FIELDS:
                return True

    updated_from = context.get("updatedFrom")
    if isinstance(updated_from, Mapping):
        if any(_normalize_identifier(field) in STATUS_FIELDS for field in updated_from):
            return True

    return any(
        _text_value(context.get(key))
        for key in ("newStatus", "new_status", "status", "state", "workflowState", "workflow_state")
    )


def _new_status(context: Mapping[str, Any]) -> str | None:
    explicit = _first_text(
        context,
        (
            "newStatus",
            "new_status",
            "newState",
            "new_state",
            "newWorkflowState",
            "new_workflow_state",
            "statusName",
            "stateName",
            "workflowStateName",
        ),
    )
    if explicit:
        return explicit

    for key in ("status", "state", "workflowState", "workflow_state"):
        value = context.get(key)
        if isinstance(value, Mapping):
            nested = _first_text(value, ("name", "title", "status", "state"))
            if nested:
                return nested
        text = _text_value(value)
        if text:
            return text

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        for field, change in changes.items():
            if _normalize_identifier(field) in STATUS_FIELDS:
                status = _status_from_change(change)
                if status:
                    return status
    elif isinstance(changes, list | tuple):
        for change in changes:
            if not isinstance(change, Mapping):
                continue
            field_name = _first_text(change, ("field", "fieldName", "name", "key"))
            if _normalize_identifier(field_name) in STATUS_FIELDS:
                status = _status_from_change(change)
                if status:
                    return status

    return None


def _status_from_change(change: Any) -> str | None:
    if isinstance(change, Mapping):
        return _first_text(change, ("newValue", "new_value", "to", "after", "name", "value"))
    return _text_value(change)


def _mapping_value(mapping: Mapping[str, Any] | None, key: str) -> Mapping[str, Any] | None:
    if not isinstance(mapping, Mapping):
        return None
    value = mapping.get(key)
    return value if isinstance(value, Mapping) else None


def _first_text(mapping: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, Mapping):
            value = _first_text(value, ("name", "title", "id"))
        text = _text_value(value)
        if text:
            return text
    return None


def _text_value(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _normalize_text(value: Any) -> str:
    text = _text_value(value) or ""
    text = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", text)
    text = re.sub(r"[^a-zA-Z0-9]+", " ", text).strip().lower()
    return re.sub(r"\s+", " ", text)


def _normalize_identifier(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", _normalize_text(value))


def main() -> int:
    payload = json.load(sys.stdin)
    result = build_issue_title_update(payload)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
