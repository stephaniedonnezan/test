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
STATUS_CHANGE_TRIGGERS = {"statuschanged", "statuschange", "statusupdated"}
UPDATE_TRIGGERS = {
    "issueupdated",
    "updatedissue",
    "update",
    "updated",
    "issueupdate",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to To Research."""
    if not isinstance(event, Mapping):
        return None

    context = _payload_context(event)
    if not _is_status_change_event(context) or _normalize_status(_extract_new_status(context)) != TARGET_STATUS:
        return None

    issue_id = _clean_string(_first_present(context, ("issueId", "issue_id", "id", "identifier", "key")))
    title = _clean_string(_first_present(context, ("title", "name")))
    if not issue_id or not title:
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": title if _has_research_prefix(title) else f"{PREFIX}: {title}",
    }


def _payload_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten common Cursor and Linear webhook payload shapes into one context."""
    context: dict[str, Any] = {}

    for path in (
        ("triggerContext",),
        ("triggerContext", "data"),
        ("triggerContext", "data", "issue"),
        ("data",),
        ("data", "issue"),
        ("issue",),
    ):
        nested = _get_path(event, path)
        if isinstance(nested, Mapping):
            context.update(nested)

    context.update(event)
    return context


def _is_status_change_event(context: Mapping[str, Any]) -> bool:
    trigger_values = [
        _normalize_event_name(value)
        for key, value in context.items()
        if key in {"trigger", "webhookType", "action", "type"} and isinstance(value, str)
    ]
    if any(value in STATUS_CHANGE_TRIGGERS for value in trigger_values):
        return True

    if any(value in UPDATE_TRIGGERS for value in trigger_values):
        return _changed_fields_include_status(context)

    # Cursor automation payloads may omit a specific trigger name but include the changed fields.
    return _changed_fields_include_status(context)


def _changed_fields_include_status(context: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "changedFields"):
        if _field_names_include_status(context.get(key)):
            return True

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        return any(_normalize_field_name(name) in STATUS_FIELDS for name in changes.keys())
    if isinstance(changes, list):
        return any(_field_names_include_status(change) for change in changes)

    return False


def _field_names_include_status(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_field_name(value) in STATUS_FIELDS
    if isinstance(value, Mapping):
        names = (
            value.get("field"),
            value.get("fieldName"),
            value.get("name"),
            value.get("key"),
            value.get("property"),
        )
        return any(_field_names_include_status(name) for name in names)
    if isinstance(value, list):
        return any(_field_names_include_status(item) for item in value)
    return False


def _extract_new_status(context: Mapping[str, Any]) -> Any:
    for key in (
        "newStatus",
        "new_status",
        "toStatus",
        "to_status",
        "statusName",
        "status",
    ):
        value = context.get(key)
        if value is not None:
            return _status_value(value)

    for key in ("state", "workflowState", "workflow_state"):
        value = context.get(key)
        if value is not None:
            return _status_value(value)

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        for key, change in changes.items():
            if _normalize_field_name(key) in STATUS_FIELDS:
                changed_value = _changed_to_value(change)
                if changed_value is not None:
                    return _status_value(changed_value)

    if isinstance(changes, list):
        for change in changes:
            if _field_names_include_status(change):
                changed_value = _changed_to_value(change)
                if changed_value is not None:
                    return _status_value(changed_value)

    return None


def _changed_to_value(change: Any) -> Any:
    if not isinstance(change, Mapping):
        return change
    for key in ("to", "toValue", "newValue", "new", "after", "value", "name"):
        value = change.get(key)
        if value is not None:
            return value
    return None


def _status_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        for key in ("name", "title", "status", "state"):
            nested = value.get(key)
            if nested is not None:
                return _status_value(nested)
    return value


def _first_present(context: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = context.get(key)
        if value is not None:
            return value
    return None


def _get_path(event: Mapping[str, Any], path: tuple[str, ...]) -> Any:
    current: Any = event
    for part in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(part)
    return current


def _clean_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _normalize_status(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = re.sub(r"([a-z])([A-Z])", r"\1 \2", value).strip().lower()
    normalized = re.sub(r"[_\-\s]+", " ", normalized)
    return normalized


def _normalize_event_name(value: str) -> str:
    with_spaces = re.sub(r"([a-z])([A-Z])", r"\1 \2", value)
    return re.sub(r"[^a-z0-9]+", "", with_spaces.lower())


def _normalize_field_name(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def main() -> int:
    payload = json.load(sys.stdin)
    update = build_issue_title_update(payload)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
