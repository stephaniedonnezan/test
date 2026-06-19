"""Build title updates for Linear issues moved to research.

The automation consumes Linear/Cursor webhook payloads and returns a small
action object when an issue status change moves into "to research".
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELDS = {
    "status",
    "state",
    "workflowstate",
    "workflowstatus",
    "teamstate",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action for qualifying Linear status changes.

    The returned action is intentionally transport-agnostic so the caller can
    perform the Linear mutation with its preferred client.
    """

    if not isinstance(event, Mapping):
        return None

    context = _event_context(event)
    if not _is_status_change_event(context):
        return None

    new_status = _extract_new_status(context)
    if _normalize_text(new_status) != TARGET_STATUS:
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


def _event_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten common Cursor and Linear payload locations into one mapping."""

    context: dict[str, Any] = {}

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        context.update(trigger_context)

    data = event.get("data")
    if isinstance(data, Mapping):
        context.update(data)
        issue = data.get("issue") or data.get("data")
        if isinstance(issue, Mapping):
            context.update(issue)

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        context.update(issue)

    # Keep top-level trigger metadata authoritative for flat automation events.
    context.update(event)
    return context


def _is_status_change_event(context: Mapping[str, Any]) -> bool:
    trigger_values = [
        context.get("trigger"),
        context.get("webhookType"),
        context.get("action"),
        context.get("type"),
        context.get("eventType"),
    ]

    if any(_is_direct_status_change(value) for value in trigger_values):
        return True

    if any(_is_issue_update(value) for value in trigger_values):
        return _updated_fields_include_status(context)

    return False


def _is_direct_status_change(value: Any) -> bool:
    normalized = _normalize_text(value)
    return normalized in {
        "status changed",
        "status change",
        "state changed",
        "workflow state changed",
        "workflow status changed",
    }


def _is_issue_update(value: Any) -> bool:
    normalized = _normalize_text(value)
    return normalized in {
        "update",
        "updated",
        "issue update",
        "issue updated",
        "updated issue",
    }


def _updated_fields_include_status(context: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        if _contains_status_field(context.get(key)):
            return True

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        return any(_field_name_is_status(field) for field in changes)

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _field_name_is_status(value)

    if isinstance(value, Mapping):
        return any(_field_name_is_status(field) for field in value)

    if isinstance(value, list | tuple | set):
        return any(_contains_status_field(item) for item in value)

    return False


def _field_name_is_status(value: Any) -> bool:
    return _compact_key(value) in _STATUS_FIELDS


def _extract_new_status(context: Mapping[str, Any]) -> str | None:
    for key in (
        "newStatus",
        "new_status",
        "toStatus",
        "to_status",
        "status",
        "state",
        "workflowState",
        "workflow_state",
    ):
        value = _string_or_name(context.get(key))
        if value:
            return value

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        for key, value in changes.items():
            if not _field_name_is_status(key):
                continue
            if isinstance(value, Mapping):
                status = _string_or_name(
                    value.get("new")
                    or value.get("to")
                    or value.get("after")
                    or value.get("current")
                )
            else:
                status = _string_or_name(value)
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
    for key in ("title", "name", "summary"):
        value = context.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _string_or_name(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            nested = value.get(key)
            if isinstance(nested, str) and nested.strip():
                return nested.strip()
    return None


def _has_prefix(title: str) -> bool:
    return title.strip().lower().startswith(PREFIX.lower())


def _normalize_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value.strip())
    normalized = re.sub(r"[^A-Za-z0-9]+", " ", spaced)
    return re.sub(r"\s+", " ", normalized).strip().lower()


def _compact_key(value: Any) -> str | None:
    normalized = _normalize_text(value)
    if normalized is None:
        return None
    return normalized.replace(" ", "")


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        json.dump(action, sys.stdout, indent=2)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
