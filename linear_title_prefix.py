"""Build Linear issue title updates for research status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"
STATUS_FIELDS = frozenset({"status", "state", "workflowstate", "workflow_state"})


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to research."""
    if not isinstance(event, Mapping):
        return None

    context = _event_context(event)
    if not _is_status_change_event(context):
        return None

    status = _status_name(context)
    if _normalize_value(status) != _normalize_value(RESEARCH_STATUS):
        return None

    issue_id = _first_string(context, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_string(context, ("title", "name"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _event_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common Cursor and Linear webhook shapes into one lookup mapping."""
    context: dict[str, Any] = {}

    for key in ("issue", "data", "triggerContext"):
        nested = event.get(key)
        if isinstance(nested, Mapping):
            context.update(_event_context(nested))

    context.update(event)
    return context


def _is_status_change_event(context: Mapping[str, Any]) -> bool:
    trigger_values = (
        context.get("trigger"),
        context.get("webhookType"),
        context.get("action"),
        context.get("type"),
    )
    normalized_triggers = {_normalize_value(value) for value in trigger_values if value}

    if any("statuschanged" in value or "statechanged" in value for value in normalized_triggers):
        return True

    if not any(value in {"update", "issueupdate", "issueupdated", "updatedissue"} for value in normalized_triggers):
        return False

    return _changed_status_fields(context)


def _changed_status_fields(context: Mapping[str, Any]) -> bool:
    updated_fields = context.get("updatedFields")
    if isinstance(updated_fields, (list, tuple, set)):
        if any(_normalize_field_name(field) in STATUS_FIELDS for field in updated_fields):
            return True
    elif isinstance(updated_fields, Mapping):
        if any(_normalize_field_name(field) in STATUS_FIELDS for field in updated_fields):
            return True
    elif isinstance(updated_fields, str):
        if _normalize_field_name(updated_fields) in STATUS_FIELDS:
            return True

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        return any(_normalize_field_name(field) in STATUS_FIELDS for field in changes)

    return False


def _status_name(context: Mapping[str, Any]) -> str | None:
    for key in ("newStatus", "new_status", "statusName", "stateName", "workflowStateName"):
        value = _string_or_name(context.get(key))
        if value:
            return value

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        for key in ("status", "state", "workflowState", "workflow_state"):
            change = changes.get(key)
            if isinstance(change, Mapping):
                value = _string_or_name(change.get("to") or change.get("newValue") or change.get("after"))
            else:
                value = _string_or_name(change)
            if value:
                return value

    for key in ("status", "state", "workflowState", "workflow_state"):
        value = _string_or_name(context.get(key))
        if value:
            return value

    return None


def _first_string(context: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = context.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _string_or_name(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            nested = value.get(key)
            if isinstance(nested, str) and nested.strip():
                return nested
    return None


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(TITLE_PREFIX.casefold())


def _normalize_value(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return re.sub(r"[^a-z0-9]+", "", spaced.casefold())


def _normalize_field_name(value: Any) -> str:
    return _normalize_value(str(value) if value is not None else "")


def main() -> int:
    """Read a JSON event from stdin and print the requested update action."""
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, indent=2, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
