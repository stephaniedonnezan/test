"""Build Linear issue title updates for research status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return an issue title update action when a Linear issue enters research."""
    if not isinstance(event, Mapping):
        return None

    context = _context_from_event(event)
    if not _is_status_change(context):
        return None

    status = _new_status(context)
    if _normalize_value(status) != TARGET_STATUS:
        return None

    issue_id = _first_text(context, ("id", "issueId", "issue_id", "identifier"))
    title = _first_text(context, ("title", "name"))
    if not issue_id or not title:
        return None

    if title.casefold().startswith(TITLE_PREFIX.casefold()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _context_from_event(event: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten common Linear and Cursor automation payload wrappers."""
    context: dict[str, Any] = {}

    for key in ("issue", "data", "triggerContext"):
        value = event.get(key)
        if isinstance(value, Mapping):
            context.update(_context_from_event(value))

    context.update(event)
    return context


def _is_status_change(context: Mapping[str, Any]) -> bool:
    trigger_values = (
        _normalize_value(value)
        for key in ("trigger", "webhookType", "action", "type")
        if (value := context.get(key)) is not None
    )

    for value in trigger_values:
        if value in {"status changed", "status change", "statuschanged"}:
            return True
        if value in {"issue updated", "updated issue", "update", "updated"}:
            return _updated_fields_include_status(context)

    return False


def _updated_fields_include_status(context: Mapping[str, Any]) -> bool:
    updated_fields = context.get("updatedFields") or context.get("updated_fields")
    if updated_fields is None:
        return False

    if isinstance(updated_fields, str):
        fields = re.split(r"[\s,]+", updated_fields)
    elif isinstance(updated_fields, Mapping):
        fields = updated_fields.keys()
    elif isinstance(updated_fields, list | tuple | set):
        fields = updated_fields
    else:
        return False

    return any(_normalize_key(str(field)) in STATUS_FIELDS for field in fields)


def _new_status(context: Mapping[str, Any]) -> str | None:
    for key in ("newStatus", "new_status", "statusName", "status_name"):
        value = _text_or_name(context.get(key))
        if value:
            return value

    for key in ("state", "workflowState", "workflow_state", "status"):
        value = _text_or_name(context.get(key))
        if value:
            return value

    return None


def _first_text(context: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = _text_or_name(context.get(key))
        if value:
            return value
    return None


def _text_or_name(value: Any) -> str | None:
    if isinstance(value, str):
        text = value.strip()
        return text or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "id", "identifier"):
            text = _text_or_name(value.get(key))
            if text:
                return text

    return None


def _normalize_value(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    normalized = re.sub(r"[^a-zA-Z0-9]+", " ", separated).strip().casefold()
    return re.sub(r"\s+", " ", normalized)


def _normalize_key(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "", value).casefold()


def main() -> int:
    payload = json.load(sys.stdin)
    update = build_issue_title_update(payload)
    if update is not None:
        json.dump(update, sys.stdout)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
