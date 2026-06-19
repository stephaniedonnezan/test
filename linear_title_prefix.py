"""Build Linear issue-title update actions for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


RESEARCH_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue title update action when a Linear issue moves to research."""
    if not isinstance(event, Mapping):
        return None

    context = _event_context(event)
    if not _is_status_change_event(context):
        return None

    new_status = _first_status(context)
    if _normalize(new_status) != TARGET_STATUS:
        return None

    issue_id = _first_text(context, ("issueId", "issue_id", "id", "identifier", "key"))
    title = _first_text(context, ("title", "name"))
    if not issue_id or not title:
        return None

    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{RESEARCH_PREFIX}: {title}",
    }


def _event_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common Cursor automation and Linear webhook nesting into one context."""
    context: dict[str, Any] = {}

    trigger_context = _mapping_value(event, "triggerContext")
    data = _mapping_value(event, "data")
    issue = _mapping_value(data, "issue") if data else None

    for source in (issue, data, trigger_context, event):
        if source:
            context.update(source)

    return context


def _is_status_change_event(context: Mapping[str, Any]) -> bool:
    for key in ("trigger", "webhookType", "action", "type"):
        value = context.get(key)
        normalized = _normalize(value)
        if normalized in {"status changed", "status change", "statuschanged"}:
            return True
        if normalized in {"issue updated", "updated issue", "update", "updated"}:
            return _changed_status_field(context)

    return _changed_status_field(context)


def _changed_status_field(context: Mapping[str, Any]) -> bool:
    updated_fields = context.get("updatedFields") or context.get("updated_fields")
    if _field_list_has_status(updated_fields):
        return True

    changes = context.get("changes") or context.get("changedFields") or context.get("changed_fields")
    if isinstance(changes, Mapping):
        return any(_normalize_field_name(field) in STATUS_FIELDS for field in changes)
    if isinstance(changes, list):
        return _field_list_has_status(changes)

    return False


def _field_list_has_status(value: Any) -> bool:
    if not isinstance(value, list):
        return False

    for item in value:
        if isinstance(item, Mapping):
            field_name = item.get("field") or item.get("name") or item.get("key")
        else:
            field_name = item
        if _normalize_field_name(field_name) in STATUS_FIELDS:
            return True
    return False


def _first_status(context: Mapping[str, Any]) -> str | None:
    for key in (
        "newStatus",
        "new_status",
        "status",
        "state",
        "workflowState",
        "workflow_state",
    ):
        value = context.get(key)
        text = _status_text(value)
        if text:
            return text

    changes = context.get("changes") or context.get("changedFields") or context.get("changed_fields")
    if isinstance(changes, Mapping):
        for field, change in changes.items():
            if _normalize_field_name(field) not in STATUS_FIELDS:
                continue
            text = _status_text_from_change(change)
            if text:
                return text

    return None


def _status_text(value: Any) -> str | None:
    if isinstance(value, str):
        text = value.strip()
        return text or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            text = _status_text(value.get(key))
            if text:
                return text

    return None


def _status_text_from_change(change: Any) -> str | None:
    if isinstance(change, Mapping):
        for key in ("to", "new", "newValue", "after", "value"):
            text = _status_text(change.get(key))
            if text:
                return text
    return _status_text(change)


def _first_text(context: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = context.get(key)
        if isinstance(value, str):
            text = value.strip()
            if text:
                return text
    return None


def _mapping_value(mapping: Mapping[str, Any] | None, key: str) -> Mapping[str, Any] | None:
    if not mapping:
        return None
    value = mapping.get(key)
    return value if isinstance(value, Mapping) else None


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(RESEARCH_PREFIX.lower())


def _normalize(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value.strip())
    return re.sub(r"[\s_-]+", " ", spaced).strip().lower()


def _normalize_field_name(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[\s_-]+", "", value).lower()


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is None:
        return 0

    json.dump(update, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
