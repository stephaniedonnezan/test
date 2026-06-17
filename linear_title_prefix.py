"""Build Linear issue title updates for Cursor research automations."""

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
    """Return an issue title update when a Linear issue moves to research."""
    if not isinstance(event, Mapping):
        return None

    payload = _payload_for_issue(event)
    if not _is_status_change(payload):
        return None

    new_status = _new_status(payload)
    if _normalize_text(new_status) != TARGET_STATUS:
        return None

    issue_id = _first_text(payload, ("issueId", "issue_id", "id", "identifier", "key"))
    title = _first_text(payload, ("title", "name"))
    if not issue_id or not title:
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": _with_research_prefix(title),
    }


def _payload_for_issue(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common Cursor and Linear webhook shapes into one flat payload."""
    payload: dict[str, Any] = {}

    for source in (
        event.get("issue"),
        event.get("data", {}).get("issue") if isinstance(event.get("data"), Mapping) else None,
        event.get("data"),
        event.get("triggerContext"),
        event,
    ):
        if isinstance(source, Mapping):
            payload.update(source)

    return payload


def _is_status_change(payload: Mapping[str, Any]) -> bool:
    trigger_values = [
        payload.get("trigger"),
        payload.get("webhookType"),
        payload.get("action"),
        payload.get("type"),
    ]
    normalized_triggers = {_normalize_text(value) for value in trigger_values if value}

    if any(value in {"status changed", "status change", "statuschanged"} for value in normalized_triggers):
        return True

    if any(value in {"issue updated", "updated issue", "update", "updated"} for value in normalized_triggers):
        return _changed_fields_include_status(payload)

    return False


def _changed_fields_include_status(payload: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        fields = payload.get(key)
        if _field_collection_includes_status(fields):
            return True

    changes = payload.get("changes")
    if isinstance(changes, Mapping):
        return any(_normalize_field_name(field) in STATUS_FIELDS for field in changes)

    return False


def _field_collection_includes_status(fields: Any) -> bool:
    if isinstance(fields, str):
        field_names = re.split(r"[\s,]+", fields)
    elif isinstance(fields, Mapping):
        field_names = fields.keys()
    elif isinstance(fields, list | tuple | set):
        field_names = fields
    else:
        return False

    return any(_normalize_field_name(field) in STATUS_FIELDS for field in field_names)


def _new_status(payload: Mapping[str, Any]) -> str | None:
    for key in ("newStatus", "new_status", "statusName", "status_name"):
        value = _text_or_name(payload.get(key))
        if value:
            return value

    changes = payload.get("changes")
    if isinstance(changes, Mapping):
        for key in ("status", "state", "workflowState", "workflow_state"):
            value = _changed_value(changes.get(key))
            if value:
                return value

    for key in ("status", "state", "workflowState", "workflow_state"):
        value = _text_or_name(payload.get(key))
        if value:
            return value

    return None


def _changed_value(change: Any) -> str | None:
    if isinstance(change, Mapping):
        for key in ("to", "newValue", "new_value", "after", "name"):
            value = _text_or_name(change.get(key))
            if value:
                return value
    return _text_or_name(change)


def _with_research_prefix(title: str) -> str:
    stripped_title = title.strip()
    if stripped_title.lower().startswith(PREFIX.lower()):
        return stripped_title
    return f"{PREFIX}: {stripped_title}"


def _first_text(payload: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = _text_or_name(payload.get(key))
        if value:
            return value
    return None


def _text_or_name(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    if isinstance(value, Mapping):
        return _first_text(value, ("name", "title", "id", "identifier", "key"))
    return None


def _normalize_text(value: Any) -> str:
    text = _text_or_name(value) or ""
    text = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", text)
    text = re.sub(r"[^a-zA-Z0-9]+", " ", text)
    return " ".join(text.casefold().split())


def _normalize_field_name(value: Any) -> str:
    text = _text_or_name(value) or ""
    return re.sub(r"[^a-zA-Z0-9]+", "", text).casefold()


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
