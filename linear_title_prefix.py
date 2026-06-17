"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}
TRIGGER_FIELDS = {"trigger", "webhooktype", "webhook_type", "action", "type"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title-update action when an issue moves to the research status."""
    if not isinstance(event, Mapping):
        return None

    context = _merge_context(event)
    if not _is_status_change_event(context):
        return None

    status = _extract_new_status(context)
    if _normalize(status) != TARGET_STATUS:
        return None

    issue_id = _extract_issue_id(context)
    title = _extract_title(context)
    if not issue_id or not title:
        return None

    if _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _merge_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten common Cursor and Linear payload shapes with outer fields winning."""
    context: dict[str, Any] = {}

    for key in ("data", "issue", "triggerContext"):
        value = event.get(key)
        if isinstance(value, Mapping):
            context.update(_merge_context(value))

    context.update(event)
    return context


def _is_status_change_event(context: Mapping[str, Any]) -> bool:
    trigger_values = [
        value
        for key, value in context.items()
        if _normalize_key(key) in TRIGGER_FIELDS and isinstance(value, str)
    ]

    if any("status changed" in _normalize(value) or "state changed" in _normalize(value) for value in trigger_values):
        return True

    if any(_normalize(value) in {"update", "issue updated", "updated issue"} for value in trigger_values):
        return _updated_fields_include_status(context)

    return _updated_fields_include_status(context) and _extract_new_status(context) is not None


def _updated_fields_include_status(context: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        fields = context.get(key)
        if _field_collection_includes_status(fields):
            return True

    changes = context.get("changes") or context.get("updatedFrom")
    if isinstance(changes, Mapping):
        return any(_normalize_key(key) in STATUS_FIELDS for key in changes)

    return False


def _field_collection_includes_status(fields: Any) -> bool:
    if isinstance(fields, str):
        return _normalize_key(fields) in STATUS_FIELDS

    if isinstance(fields, Mapping):
        return any(_normalize_key(key) in STATUS_FIELDS for key in fields)

    if isinstance(fields, Iterable):
        return any(isinstance(field, str) and _normalize_key(field) in STATUS_FIELDS for field in fields)

    return False


def _extract_new_status(context: Mapping[str, Any]) -> str | None:
    for key in ("newStatus", "new_status", "statusName", "status_name", "newState", "new_state"):
        status = _coerce_name(context.get(key))
        if status:
            return status

    for key in ("status", "state", "workflowState", "workflow_state"):
        status = _coerce_name(context.get(key))
        if status:
            return status

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        for key in ("status", "state", "workflowState", "workflow_state"):
            value = changes.get(key)
            if isinstance(value, Mapping):
                status = _coerce_name(value.get("to") or value.get("new") or value.get("newValue"))
                if status:
                    return status

    return None


def _extract_issue_id(context: Mapping[str, Any]) -> str | None:
    for key in ("issueId", "issue_id", "identifier", "key", "id"):
        value = context.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _extract_title(context: Mapping[str, Any]) -> str | None:
    title = context.get("title")
    if isinstance(title, str) and title.strip():
        return title.strip()
    return None


def _coerce_name(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()

    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            result = _coerce_name(value.get(key))
            if result:
                return result

    return None


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def _normalize(value: str | None) -> str:
    if not value:
        return ""

    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    lowered = spaced.lower()
    words = re.sub(r"[^a-z0-9]+", " ", lowered).strip().split()
    return " ".join(words)


def _normalize_key(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^a-z0-9_]", "", value.lower())


def main() -> int:
    payload = json.load(sys.stdin)
    update = build_issue_title_update(payload)
    if update is None:
        return 0

    print(json.dumps(update, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
