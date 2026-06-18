"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
TITLE_SEPARATOR = ": "

STATUS_FIELDS = {
    "status",
    "state",
    "workflowstate",
    "workflowstatus",
    "statusid",
    "stateid",
    "workflowstateid",
    "workflowstatusid",
}

DIRECT_STATUS_CHANGE_TRIGGERS = {
    "status changed",
    "status change",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
    "workflow status changed",
    "workflow status change",
}

GENERIC_ISSUE_UPDATE_TRIGGERS = {
    "issue updated",
    "updated issue",
    "update",
    "updated",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update action when an issue moves to the research status.

    The function accepts both flat Cursor automation payloads, where issue fields
    live under ``triggerContext``, and nested Linear webhook payloads that place
    issue details under ``data.issue``.
    """

    if not isinstance(event, Mapping):
        return None

    context = _issue_context(event)
    if not _is_status_change_event(context):
        return None

    status = _new_status(context)
    if _normalize_status(status) != TARGET_STATUS:
        return None

    issue_id = _string_value(context, "issueId", "issue_id", "identifier", "key", "id")
    title = _string_value(context, "title", "name")
    if not issue_id or not title or _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}{TITLE_SEPARATOR}{title}",
    }


def _issue_context(event: Mapping[str, Any]) -> dict[str, Any]:
    context: dict[str, Any] = {}

    for key in ("issue", "data", "triggerContext"):
        value = event.get(key)
        if isinstance(value, Mapping):
            context.update(_issue_context(value))

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            context.update(_issue_context(issue))

    context.update(event)
    return context


def _is_status_change_event(context: Mapping[str, Any]) -> bool:
    trigger_values = [
        _normalize_token(value)
        for value in _values_for_keys(context, "trigger", "webhookType", "action", "type")
        if isinstance(value, str)
    ]

    if any(value in DIRECT_STATUS_CHANGE_TRIGGERS for value in trigger_values):
        return True

    if any(value in GENERIC_ISSUE_UPDATE_TRIGGERS for value in trigger_values):
        return _changed_status_field(context)

    return _changed_status_field(context) and bool(_new_status(context))


def _changed_status_field(context: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        if _contains_status_field(context.get(key)):
            return True

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        return any(_is_status_field(key) for key in changes)
    if isinstance(changes, Iterable) and not isinstance(changes, (str, bytes, Mapping)):
        for change in changes:
            if isinstance(change, Mapping):
                field = _string_value(change, "field", "key", "name")
                if field and _is_status_field(field):
                    return True
            elif isinstance(change, str) and _is_status_field(change):
                return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes, Mapping)):
        return any(isinstance(item, str) and _is_status_field(item) for item in value)
    return False


def _is_status_field(field: str) -> bool:
    return _normalize_field(field) in STATUS_FIELDS


def _new_status(context: Mapping[str, Any]) -> str | None:
    direct = _string_value(
        context,
        "newStatus",
        "new_status",
        "toStatus",
        "to_status",
        "statusName",
        "status_name",
        "stateName",
        "state_name",
        "workflowStateName",
        "workflow_state_name",
    )
    if direct:
        return direct

    for key in ("changes", "status", "state", "workflowState", "workflow_state"):
        value = context.get(key)
        status = _status_from_change(value)
        if status:
            return status

    return None


def _status_from_change(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None

    if isinstance(value, Mapping):
        direct = _string_value(value, "to", "new", "newValue", "new_value", "name", "value")
        if direct:
            return direct

        for status_key in ("status", "state", "workflowState", "workflow_state"):
            nested = value.get(status_key)
            status = _status_from_change(nested)
            if status:
                return status

    return None


def _values_for_keys(context: Mapping[str, Any], *keys: str) -> Iterable[Any]:
    for key in keys:
        if key in context:
            yield context[key]


def _string_value(context: Mapping[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = context.get(key)
        if isinstance(value, str):
            stripped = value.strip()
            if stripped:
                return stripped
    return None


def _has_prefix(title: str) -> bool:
    return title.casefold().lstrip().startswith(PREFIX.casefold())


def _normalize_status(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = _normalize_token(value)
    return normalized or None


def _normalize_token(value: str) -> str:
    value = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    value = re.sub(r"[^A-Za-z0-9]+", " ", value)
    return " ".join(value.casefold().split())


def _normalize_field(value: str) -> str:
    return _normalize_token(value).replace(" ", "")


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        json.dump(update, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
