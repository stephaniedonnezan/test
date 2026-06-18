"""Build Linear title update actions for issues moved to To Research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "workflow state", "workflow status"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action for To Research status changes."""
    if not isinstance(event, Mapping):
        return None

    context = _event_context(event)
    if not _is_status_change_event(context):
        return None

    status = _new_status(context)
    if _normalize_text(status) != TARGET_STATUS:
        return None

    issue_id = _issue_id(context)
    title = _issue_title(context)
    if not issue_id or not title or _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _event_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge the common Cursor and Linear webhook nesting shapes."""
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

    # Preserve nested payloads for status/title/id fallbacks after top-level
    # metadata has been allowed to override stale issue data.
    if isinstance(trigger_context, Mapping):
        context["triggerContext"] = trigger_context
    if isinstance(data, Mapping):
        context["data"] = data
    if isinstance(issue, Mapping):
        context["issue"] = issue

    return context


def _is_status_change_event(context: Mapping[str, Any]) -> bool:
    trigger_values = [
        context.get(key)
        for key in ("trigger", "webhookType", "action", "type")
        if isinstance(context.get(key), str)
    ]

    if any(_is_direct_status_change(value) for value in trigger_values):
        return True

    if any(_is_generic_issue_update(value) for value in trigger_values):
        return _has_status_change_metadata(context)

    return _has_status_change_metadata(context) and not trigger_values


def _is_direct_status_change(value: str) -> bool:
    normalized = _normalize_text(value)
    compact = normalized.replace(" ", "")
    return compact in {
        "statuschanged",
        "statuschange",
        "statechanged",
        "statechange",
        "workflowstatechanged",
        "workflowstatechange",
    }


def _is_generic_issue_update(value: str) -> bool:
    normalized = _normalize_text(value)
    return normalized in {"update", "updated", "issue update", "issue updated", "updated issue"}


def _has_status_change_metadata(context: Mapping[str, Any]) -> bool:
    updated_fields = context.get("updatedFields") or context.get("updated_fields")
    if _contains_status_field(updated_fields):
        return True

    changes = context.get("changes") or context.get("changed") or context.get("updatedFrom")
    if isinstance(changes, Mapping):
        return any(_is_status_field(key) for key in changes)
    if isinstance(changes, list):
        return _contains_status_field(changes)

    return False


def _contains_status_field(fields: Any) -> bool:
    if isinstance(fields, str):
        return _is_status_field(fields)
    if isinstance(fields, Mapping):
        return any(_is_status_field(key) for key in fields)
    if isinstance(fields, list | tuple | set):
        return any(_contains_status_field(field) for field in fields)
    return False


def _is_status_field(field: Any) -> bool:
    normalized = _normalize_text(field)
    return normalized in STATUS_FIELD_NAMES


def _new_status(context: Mapping[str, Any]) -> str | None:
    for key in (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "status",
        "state",
        "workflowState",
        "workflow_status",
        "workflowStatus",
    ):
        value = _status_name(context.get(key))
        if value:
            return value

    for container_key in ("triggerContext", "data", "issue"):
        nested = context.get(container_key)
        if isinstance(nested, Mapping):
            value = _new_status(nested)
            if value:
                return value

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        for key, value in changes.items():
            if not _is_status_field(key):
                continue
            if isinstance(value, Mapping):
                status = _status_name(value.get("to") or value.get("new") or value.get("after"))
            else:
                status = _status_name(value)
            if status:
                return status

    return None


def _status_name(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    if isinstance(value, Mapping):
        for key in ("name", "status", "state", "title"):
            status = _status_name(value.get(key))
            if status:
                return status
    return None


def _issue_id(context: Mapping[str, Any]) -> str | None:
    return _first_string(context, ("issueId", "issue_id", "identifier", "key", "id"))


def _issue_title(context: Mapping[str, Any]) -> str | None:
    return _first_string(context, ("title", "name"))


def _first_string(context: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = context.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    for container_key in ("triggerContext", "data", "issue"):
        nested = context.get(container_key)
        if isinstance(nested, Mapping):
            value = _first_string(nested, keys)
            if value:
                return value

    return None


def _has_prefix(title: str) -> bool:
    return title.lstrip().lower().startswith(PREFIX.lower())


def _normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    spaced = re.sub(r"[_\-/]+", " ", spaced)
    return " ".join(spaced.strip().casefold().split())


def main() -> int:
    event = json.load(sys.stdin)
    result = build_issue_title_update(event)
    if result is not None:
        json.dump(result, sys.stdout)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
