"""Build Linear issue title updates for Cursor research automations."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


RESEARCH_STATUS = "to research"
TITLE_MARKER = "Cursor researching"

_STATUS_CHANGE_FIELDS = {"status", "state", "stateid", "workflowstate", "workflowstateid"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when an issue moves to "to research".

    Cursor automations pass a flat ``triggerContext`` payload, while Linear
    webhooks commonly use nested ``data`` / ``updatedFrom`` objects. This
    function accepts both shapes and returns ``None`` when the event should not
    update the issue title.
    """

    context = _event_context(event)
    if not _is_status_change_event(context):
        return None

    new_status = _new_status_name(context)
    if _normalize_status(new_status) != RESEARCH_STATUS:
        return None

    issue_id = _first_string(
        context.get("issueId"),
        context.get("issueID"),
        context.get("id"),
        _get(context, "data", "id"),
        _get(context, "issue", "id"),
    )
    title = _first_string(
        context.get("title"),
        _get(context, "data", "title"),
        _get(context, "issue", "title"),
    )

    if issue_id is None or title is None or _has_title_marker(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_MARKER}: {title}",
    }


def _event_context(event: Mapping[str, Any]) -> Mapping[str, Any]:
    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        return trigger_context
    return event


def _is_status_change_event(context: Mapping[str, Any]) -> bool:
    direct_trigger = _normalize_status(
        _first_string(
            context.get("trigger"),
            context.get("eventType"),
            context.get("type"),
            context.get("webhookType"),
        )
    )
    if direct_trigger in {"status changed", "status change", "status_changed"}:
        return True

    if _contains_status_field(context.get("updatedFields")):
        return True

    changes = context.get("changes")
    if _contains_status_change(changes):
        return True

    updated_from = context.get("updatedFrom")
    if isinstance(updated_from, Mapping):
        return any(_is_status_field(key) for key in updated_from)

    return False


def _new_status_name(context: Mapping[str, Any]) -> str | None:
    for value in (
        context.get("newStatus"),
        context.get("new_status"),
        context.get("statusName"),
        context.get("stateName"),
        context.get("workflowStateName"),
        _get(context, "status", "name"),
        _get(context, "state", "name"),
        _get(context, "workflowState", "name"),
        _get(context, "data", "status", "name"),
        _get(context, "data", "state", "name"),
        _get(context, "data", "workflowState", "name"),
    ):
        status = _first_string(value)
        if status:
            return status

    return _status_from_changes(context.get("changes"))


def _status_from_changes(changes: Any) -> str | None:
    if isinstance(changes, Mapping):
        for key, value in changes.items():
            if _is_status_field(str(key)):
                status = _changed_to_value(value)
                if status:
                    return status
        return None

    if isinstance(changes, Sequence) and not isinstance(changes, (str, bytes, bytearray)):
        for change in changes:
            if not isinstance(change, Mapping):
                continue
            field = _first_string(
                change.get("field"),
                change.get("name"),
                change.get("key"),
                change.get("path"),
            )
            if field and _is_status_field(field):
                status = _changed_to_value(change)
                if status:
                    return status

    return None


def _changed_to_value(change: Any) -> str | None:
    if isinstance(change, str):
        return change

    if isinstance(change, Mapping):
        for key in ("to", "new", "newValue", "after", "value", "current"):
            status = _status_value(change.get(key))
            if status:
                return status
        return _status_value(change)

    return None


def _status_value(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, Mapping):
        return _first_string(value.get("name"), value.get("title"), value.get("value"))
    return None


def _contains_status_change(changes: Any) -> bool:
    if isinstance(changes, Mapping):
        return any(_is_status_field(str(key)) for key in changes)

    if isinstance(changes, Sequence) and not isinstance(changes, (str, bytes, bytearray)):
        for change in changes:
            if not isinstance(change, Mapping):
                continue
            field = _first_string(
                change.get("field"),
                change.get("name"),
                change.get("key"),
                change.get("path"),
            )
            if field and _is_status_field(field):
                return True

    return False


def _contains_status_field(fields: Any) -> bool:
    if isinstance(fields, str):
        return _is_status_field(fields)
    if isinstance(fields, Sequence):
        return any(isinstance(field, str) and _is_status_field(field) for field in fields)
    return False


def _is_status_field(field: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]", "", field.lower())
    return normalized in _STATUS_CHANGE_FIELDS


def _normalize_status(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.replace("_", " ").replace("-", " ").strip().lower()
    return re.sub(r"\s+", " ", normalized)


def _has_title_marker(title: str) -> bool:
    return title.strip().lower().startswith(TITLE_MARKER.lower())


def _get(data: Mapping[str, Any], *path: str) -> Any:
    value: Any = data
    for key in path:
        if not isinstance(value, Mapping):
            return None
        value = value.get(key)
    return value


def _first_string(*values: Any) -> str | None:
    for value in values:
        if isinstance(value, str):
            stripped = value.strip()
            if stripped:
                return stripped
    return None


def main() -> int:
    event = json.load(sys.stdin)
    if not isinstance(event, Mapping):
        print("null")
        return 0
    print(json.dumps(build_issue_title_update(event)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
