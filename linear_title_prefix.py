"""Build Linear issue title updates for Cursor research automation.

The automation should add ``Cursor researching`` to an issue title only when a
Linear issue status changes to ``to research``.  This module is deliberately
side-effect free: callers can inspect the returned action and perform the
actual Linear mutation with their own API client.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}
STATUS_CHANGE_TRIGGERS = {
    "statuschange",
    "statuschanged",
}
ISSUE_UPDATE_TRIGGERS = {
    "issueupdated",
    "updatedissue",
    "update",
    "updated",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return the Linear title update action for a research-status event.

    The expected action is returned only when the payload describes an issue
    status change to ``to research``.  Titles already beginning with
    ``Cursor researching`` are ignored so repeated webhook delivery remains
    idempotent.
    """

    if not isinstance(event, Mapping):
        return None

    context = _flatten_event(event)
    if not _is_status_change_event(event, context):
        return None

    status = _changed_status(context)
    if _normalize_value(status) != _normalize_value(TARGET_STATUS):
        return None

    issue_id = _first_text(context, ("issueId", "issue_id", "id", "identifier", "key"))
    title = _first_text(context, ("title", "name"))
    if not issue_id or not title or _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _flatten_event(event: Mapping[str, Any]) -> dict[str, Any]:
    """Collect top-level automation metadata and nested Linear issue fields."""

    context: dict[str, Any] = {}

    for key in ("data", "issue", "triggerContext"):
        nested = event.get(key)
        if isinstance(nested, Mapping):
            context.update(_flatten_event(nested))

    data = event.get("data")
    if isinstance(data, Mapping):
        nested_issue = data.get("issue")
        if isinstance(nested_issue, Mapping):
            context.update(_flatten_event(nested_issue))

    context.update(event)
    return context


def _is_status_change_event(event: Mapping[str, Any], context: Mapping[str, Any]) -> bool:
    values = _event_type_values(event)
    if any(value in STATUS_CHANGE_TRIGGERS for value in values):
        return True

    if any(value in ISSUE_UPDATE_TRIGGERS for value in values):
        return _updated_fields_include_status(context) or _changes_include_status(context)

    return False


def _event_type_values(event: Mapping[str, Any]) -> set[str]:
    values: set[str] = set()

    def visit(value: Any) -> None:
        if isinstance(value, Mapping):
            for key in ("trigger", "webhookType", "action", "type", "eventType"):
                candidate = value.get(key)
                if isinstance(candidate, str):
                    values.add(_normalize_value(candidate))
            for key in ("data", "issue", "triggerContext"):
                nested = value.get(key)
                if isinstance(nested, Mapping):
                    visit(nested)

    visit(event)
    return values


def _updated_fields_include_status(context: Mapping[str, Any]) -> bool:
    updated_fields = context.get("updatedFields") or context.get("updated_fields")
    if not isinstance(updated_fields, (list, tuple, set)):
        return False

    return any(_normalize_field(field) in STATUS_FIELDS for field in updated_fields)


def _changes_include_status(context: Mapping[str, Any]) -> bool:
    changes = context.get("changes")
    if isinstance(changes, Mapping):
        return any(_normalize_field(field) in STATUS_FIELDS for field in changes)

    if isinstance(changes, (list, tuple)):
        for change in changes:
            if isinstance(change, Mapping):
                field = change.get("field") or change.get("name")
                if _normalize_field(field) in STATUS_FIELDS:
                    return True
            elif _normalize_field(change) in STATUS_FIELDS:
                return True

    return False


def _changed_status(context: Mapping[str, Any]) -> str | None:
    for key in ("newStatus", "new_status", "status"):
        value = context.get(key)
        text = _extract_name(value)
        if text:
            return text

    for key in ("state", "workflowState", "workflow_state"):
        value = context.get(key)
        text = _extract_name(value)
        if text:
            return text

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        for field, value in changes.items():
            if _normalize_field(field) in STATUS_FIELDS:
                text = _extract_changed_value(value)
                if text:
                    return text

    if isinstance(changes, (list, tuple)):
        for change in changes:
            if not isinstance(change, Mapping):
                continue
            field = change.get("field") or change.get("name")
            if _normalize_field(field) in STATUS_FIELDS:
                text = _extract_changed_value(change)
                if text:
                    return text

    return None


def _extract_changed_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("newValue", "new_value", "to", "after", "value", "name"):
            text = _extract_name(value.get(key))
            if text:
                return text
    return _extract_name(value)


def _extract_name(value: Any) -> str | None:
    if isinstance(value, str):
        text = value.strip()
        return text or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "value"):
            text = _extract_name(value.get(key))
            if text:
                return text

    return None


def _first_text(context: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        text = _extract_name(context.get(key))
        if text:
            return text
    return None


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def _normalize_field(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _normalize_value(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    with_spaces = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", value)
    return re.sub(r"[^a-z0-9]+", "", with_spaces.lower())


def main() -> int:
    action = build_issue_title_update(json.load(sys.stdin))
    if action is not None:
        print(json.dumps(action, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
