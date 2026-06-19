"""Build Linear issue title updates for Cursor research transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow_state"}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title-update action when a Linear issue moves to to research."""
    if not isinstance(event, Mapping):
        return None

    context = _extract_context(event)
    if not _is_status_change(context):
        return None

    status = _extract_new_status(context)
    if _normalize_text(status) != _normalize_text(TARGET_STATUS):
        return None

    issue_id = _first_text(context, ("issueId", "issue_id", "id", "identifier", "key"))
    title = _first_text(context, ("title", "name"))
    if not issue_id or not title:
        return None

    if title.casefold().startswith(PREFIX.casefold()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _extract_context(event: Mapping[str, Any]) -> dict[str, Any]:
    context: dict[str, Any] = {}

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        context.update(trigger_context)

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            context.update(issue)
        context.update(data)

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        context.update(issue)

    context.update(event)
    return context


def _is_status_change(context: Mapping[str, Any]) -> bool:
    event_names = [
        _normalize_text(context.get(key))
        for key in ("trigger", "webhookType", "action", "type")
    ]
    if any(name in {"status changed", "statuschanged"} for name in event_names):
        return True

    if any(name in {"issue updated", "updated issue", "update", "updated"} for name in event_names):
        return _changed_fields_include_status(context)

    return _changed_fields_include_status(context)


def _changed_fields_include_status(context: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields"):
        fields = context.get(key)
        if _field_names_include_status(fields):
            return True

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        return _field_names_include_status(changes.keys())

    return False


def _field_names_include_status(fields: Any) -> bool:
    if isinstance(fields, str):
        candidates = [fields]
    elif isinstance(fields, Mapping):
        candidates = fields.keys()
    elif isinstance(fields, Iterable):
        candidates = fields
    else:
        return False

    return any(_normalize_field_name(field) in STATUS_FIELD_NAMES for field in candidates)


def _extract_new_status(context: Mapping[str, Any]) -> str | None:
    for key in (
        "newStatus",
        "new_status",
        "status",
        "statusName",
        "state",
        "workflowState",
        "workflow_state",
    ):
        status = _text_or_name(context.get(key))
        if status:
            return status

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        for key in ("status", "state", "workflowState", "workflow_state"):
            status = _status_from_change(changes.get(key))
            if status:
                return status

    return None


def _status_from_change(change: Any) -> str | None:
    if isinstance(change, Mapping):
        for key in ("newValue", "new_value", "to", "after", "name"):
            status = _text_or_name(change.get(key))
            if status:
                return status

    return _text_or_name(change)


def _text_or_name(value: Any) -> str | None:
    if isinstance(value, str):
        text = value.strip()
        return text or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "status"):
            text = _text_or_name(value.get(key))
            if text:
                return text

    return None


def _first_text(context: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        text = _text_or_name(context.get(key))
        if text:
            return text
    return None


def _normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    normalized = re.sub(r"[^a-z0-9]+", " ", spaced.casefold()).strip()
    return re.sub(r"\s+", " ", normalized)


def _normalize_field_name(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def main() -> int:
    event = json.load(sys.stdin)
    result = build_issue_title_update(event)
    if result is not None:
        print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
