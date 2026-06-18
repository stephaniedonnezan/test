"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow state"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to research."""

    if not isinstance(event, Mapping):
        return None

    context = _event_context(event)
    if not _is_status_change_event(context):
        return None

    new_status = _new_status(context)
    if _normalize_text(new_status) != _normalize_text(TARGET_STATUS):
        return None

    issue_id = _first_string(context, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_string(context, ("title", "name"))
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


def _event_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten common Cursor and Linear webhook nesting into one lookup map."""

    context: dict[str, Any] = {}

    for key in ("data", "issue", "triggerContext"):
        value = event.get(key)
        if isinstance(value, Mapping):
            context.update(_event_context(value))

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            context.update(_event_context(issue))

    for key, value in event.items():
        if key in {"data", "issue", "triggerContext"} and isinstance(value, Mapping):
            continue
        context[key] = value

    return context


def _is_status_change_event(context: Mapping[str, Any]) -> bool:
    event_names = (
        _normalize_text(value)
        for key in ("trigger", "webhookType", "action", "type")
        for value in (context.get(key),)
    )
    if any(name in {"status changed", "statuschange", "statuschanged"} for name in event_names):
        return True

    updated_fields = _updated_fields(context)
    if not updated_fields:
        return False

    normalized_fields = {_normalize_text(field) for field in updated_fields}
    return any(field in STATUS_FIELDS for field in normalized_fields)


def _updated_fields(context: Mapping[str, Any]) -> set[str]:
    fields: set[str] = set()

    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        value = context.get(key)
        if isinstance(value, str):
            fields.add(value)
        elif isinstance(value, list):
            fields.update(str(item) for item in value if item is not None)

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        fields.update(str(key) for key in changes)
    elif isinstance(changes, list):
        for change in changes:
            if isinstance(change, Mapping):
                fields.update(
                    str(change[key])
                    for key in ("field", "name", "key")
                    if change.get(key) is not None
                )

    return fields


def _new_status(context: Mapping[str, Any]) -> str | None:
    direct = _first_string(
        context,
        (
            "newStatus",
            "new_status",
            "status",
            "state",
            "workflowState",
            "workflow_state",
        ),
    )
    if direct:
        return direct

    for key in ("state", "status", "workflowState", "workflow_state"):
        value = context.get(key)
        if isinstance(value, Mapping):
            nested = _first_string(value, ("name", "title", "type"))
            if nested:
                return nested

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        for key in ("status", "state", "workflowState", "workflow_state"):
            value = changes.get(key)
            nested = _change_new_value(value)
            if nested:
                return nested
    elif isinstance(changes, list):
        for change in changes:
            if not isinstance(change, Mapping):
                continue
            field = _normalize_text(_first_string(change, ("field", "name", "key")))
            if field in STATUS_FIELDS:
                nested = _change_new_value(change)
                if nested:
                    return nested

    return None


def _change_new_value(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if not isinstance(value, Mapping):
        return None

    direct = _first_string(value, ("newValue", "new_value", "to", "name", "title"))
    if direct:
        return direct

    for key in ("newValue", "new_value", "to"):
        nested = value.get(key)
        if isinstance(nested, Mapping):
            direct = _first_string(nested, ("name", "title", "type"))
            if direct:
                return direct

    return None


def _first_string(context: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = context.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""

    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", str(value))
    return re.sub(r"[^a-z0-9]+", " ", separated.lower()).strip()


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def main() -> int:
    payload = json.load(sys.stdin)
    update = build_issue_title_update(payload)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
