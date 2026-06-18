"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow status", "workflow state"}
DIRECT_STATUS_CHANGE_EVENTS = {
    "status changed",
    "status change",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
    "workflow status changed",
    "workflow status change",
}
GENERIC_UPDATE_EVENTS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to to-research."""

    if not isinstance(event, Mapping):
        return None

    context = _collect_context(event)
    if not _is_status_change(context):
        return None

    status = _new_status(context)
    if _normalize(status) != TARGET_STATUS:
        return None

    issue_id = _string_value(context, "issueId", "issue_id", "identifier", "key", "id")
    title = _string_value(context, "title", "name")
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _collect_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten common Cursor and Linear issue webhook containers."""

    context: dict[str, Any] = {}
    for container in _walk_mappings(event):
        context.update(container)

    # Top-level fields should win over nested issue fields because trigger metadata
    # and explicit new-status values are usually attached to the outer event.
    context.update(event)
    return context


def _walk_mappings(value: Any) -> list[Mapping[str, Any]]:
    if not isinstance(value, Mapping):
        return []

    mappings: list[Mapping[str, Any]] = []
    for key in ("issue", "data", "triggerContext", "state", "workflowState", "status"):
        nested = value.get(key)
        if isinstance(nested, Mapping):
            mappings.extend(_walk_mappings(nested))
            mappings.append(nested)
    return mappings


def _is_status_change(context: Mapping[str, Any]) -> bool:
    event_names = [
        _normalize(context.get(key))
        for key in ("trigger", "webhookType", "action", "type", "event")
        if context.get(key) is not None
    ]

    if any(name in DIRECT_STATUS_CHANGE_EVENTS for name in event_names):
        return True

    has_generic_update = any(name in GENERIC_UPDATE_EVENTS for name in event_names)
    return has_generic_update and _change_metadata_mentions_status(context)


def _change_metadata_mentions_status(context: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "changedFields"):
        if _field_list_mentions_status(context.get(key)):
            return True

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        return any(_is_status_field(key) for key in changes)

    return _field_list_mentions_status(changes)


def _field_list_mentions_status(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)

    if isinstance(value, Mapping):
        return any(_is_status_field(key) for key in value)

    if isinstance(value, list | tuple | set):
        return any(_field_list_mentions_status(item) for item in value)

    return False


def _is_status_field(value: Any) -> bool:
    normalized = _normalize(value)
    return normalized in STATUS_FIELDS or "status" in normalized or "state" in normalized


def _new_status(context: Mapping[str, Any]) -> str | None:
    explicit = _string_value(
        context,
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "statusName",
        "stateName",
        "workflowStateName",
    )
    if explicit:
        return explicit

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        for key, value in changes.items():
            if _is_status_field(key):
                changed_value = _extract_changed_value(value)
                if changed_value:
                    return changed_value

    return _string_value(context, "status", "state", "workflowState")


def _extract_changed_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        return _string_value(value, "to", "new", "after", "value", "name")

    if isinstance(value, str):
        return value

    return None


def _string_value(mapping: Mapping[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, Mapping):
            nested_name = _string_value(value, "name", "title", "id", "identifier", "key")
            if nested_name:
                return nested_name
        elif value is not None:
            text = str(value).strip()
            if text:
                return text
    return None


def _normalize(value: Any) -> str:
    if value is None:
        return ""

    text = str(value)
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[_\-/]+", " ", text)
    text = re.sub(r"[^a-zA-Z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
