"""Build Linear issue title updates for Cursor research status changes.

The automation runner can pass either a compact Cursor trigger context or a
native Linear webhook payload.  This module keeps the behavior deterministic:
only status-change events that move to "to research" produce a title update.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_CHANGE_FIELD_NAMES = {
    "status",
    "state",
    "workflowstate",
    "workflow state",
    "workflow_status",
    "workflow status",
}
_DIRECT_STATUS_CHANGE_EVENTS = {
    "status changed",
    "status change",
    "status updated",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
}
_GENERIC_UPDATE_EVENTS = {
    "update",
    "updated",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action for research status changes.

    The returned dictionary is intentionally plain JSON-serializable so callers
    can pass it directly to an automation adapter.
    """

    if not isinstance(event, Mapping):
        return None

    context = _merged_context(event)
    if not _is_status_change_event(event, context):
        return None

    new_status = _extract_new_status(event, context)
    if _normalize_text(new_status) != TARGET_STATUS:
        return None

    issue_id = _first_text(
        context,
        ("issueId", "issue_id", "identifier", "key", "id"),
    )
    title = _first_text(context, ("title", "name"))
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


def _merged_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common wrapper payloads from least to most specific metadata."""

    merged: dict[str, Any] = {}
    for candidate in _context_candidates(event):
        merged.update(candidate)
    return merged


def _context_candidates(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    candidates: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping):
            candidates.append(value)

    add(_at_path(event, ("data", "issue")))
    add(_at_path(event, ("issue",)))
    add(_at_path(event, ("data",)))
    add(_at_path(event, ("triggerContext",)))
    add(_at_path(event, ("automation_trigger_info", "triggerContext")))
    add(event)
    return candidates


def _at_path(value: Mapping[str, Any], path: Sequence[str]) -> Any:
    current: Any = value
    for key in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current


def _is_status_change_event(
    event: Mapping[str, Any],
    context: Mapping[str, Any],
) -> bool:
    trigger_values = _event_type_values(event, context)
    if any(value in _DIRECT_STATUS_CHANGE_EVENTS for value in trigger_values):
        return True

    has_generic_update = any(value in _GENERIC_UPDATE_EVENTS for value in trigger_values)
    return has_generic_update and _updated_fields_include_status(event, context)


def _event_type_values(
    event: Mapping[str, Any],
    context: Mapping[str, Any],
) -> set[str]:
    keys = ("trigger", "webhookType", "action", "type", "event", "eventType")
    values: set[str] = set()
    for source in (context, event):
        for key in keys:
            normalized = _normalize_text(source.get(key))
            if normalized:
                values.add(normalized)
    return values


def _updated_fields_include_status(
    event: Mapping[str, Any],
    context: Mapping[str, Any],
) -> bool:
    for source in (*_context_candidates(event), context):
        for key in (
            "updatedFields",
            "updated_fields",
            "changedFields",
            "changed_fields",
        ):
            if _field_collection_includes_status(source.get(key)):
                return True

        changes = source.get("changes")
        if isinstance(changes, Mapping):
            if any(_is_status_field_name(key) for key in changes):
                return True
        elif _field_collection_includes_status(changes):
            return True

    return False


def _field_collection_includes_status(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field_name(value)
    if isinstance(value, Mapping):
        return any(_is_status_field_name(key) for key in value)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for item in value:
            if isinstance(item, Mapping):
                item_name = _first_text(item, ("field", "name", "key", "property"))
                if item_name and _is_status_field_name(item_name):
                    return True
            elif _is_status_field_name(item):
                return True
    return False


def _is_status_field_name(value: Any) -> bool:
    normalized = _normalize_key(value)
    return normalized in {_normalize_key(name) for name in _CHANGE_FIELD_NAMES}


def _extract_new_status(
    event: Mapping[str, Any],
    context: Mapping[str, Any],
) -> str | None:
    for source in (context, *_context_candidates(event)):
        status = _first_text(
            source,
            (
                "newStatus",
                "new_status",
                "toStatus",
                "to_status",
                "newState",
                "new_state",
                "statusName",
                "stateName",
                "workflowStateName",
            ),
        )
        if status:
            return status

    changed_status = _status_from_changes(event)
    if changed_status:
        return changed_status

    for source in (context, *_context_candidates(event)):
        status = _status_value(source.get("status"))
        if status:
            return status
        state = _status_value(source.get("state"))
        if state:
            return state
        workflow_state = _status_value(source.get("workflowState"))
        if workflow_state:
            return workflow_state

    return None


def _status_from_changes(event: Mapping[str, Any]) -> str | None:
    for source in _context_candidates(event):
        changes = source.get("changes")
        if not isinstance(changes, Mapping):
            continue
        for key, value in changes.items():
            if not _is_status_field_name(key):
                continue
            if isinstance(value, Mapping):
                for status_key in (
                    "newValue",
                    "new_value",
                    "to",
                    "after",
                    "current",
                    "name",
                ):
                    status = _status_value(value.get(status_key))
                    if status:
                        return status
            return _status_value(value)
    return None


def _status_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        return _first_text(value, ("name", "title", "label"))
    if isinstance(value, str):
        return value
    return None


def _first_text(source: Mapping[str, Any], keys: Sequence[str]) -> str | None:
    for key in keys:
        value = source.get(key)
        if value is None:
            continue
        if isinstance(value, str):
            stripped = value.strip()
            if stripped:
                return stripped
        elif isinstance(value, (int, float)):
            return str(value)
    return None


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def _normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    spaced = re.sub(r"[^A-Za-z0-9]+", " ", spaced)
    return re.sub(r"\s+", " ", spaced).strip().lower()


def _normalize_key(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
