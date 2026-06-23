"""Build Linear issue title updates for Cursor research automation."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_CHANGE_EVENTS = {
    "status changed",
    "state changed",
    "workflow state changed",
    "workflowstate changed",
}
_ISSUE_UPDATE_EVENTS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}
_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "stateid",
    "state id",
    "workflowstate",
    "workflow state",
    "workflowstateid",
    "workflow state id",
}
_EXPLICIT_NEW_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newStatusName",
    "new_status_name",
    "newState",
    "new_state",
    "newStateName",
    "new_state_name",
    "newWorkflowState",
    "new_workflow_state",
    "newWorkflowStateName",
    "new_workflow_state_name",
)


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to research."""
    if not isinstance(event, Mapping):
        return None

    context_maps = _context_maps(event)
    if not _is_status_change_to_research(event, context_maps):
        return None

    issue_id = _issue_id(context_maps)
    title = _issue_title(context_maps)
    if not issue_id or not title:
        return None

    if title.casefold().startswith(PREFIX.casefold()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _is_status_change_to_research(
    event: Mapping[str, Any], context_maps: list[Mapping[str, Any]]
) -> bool:
    event_types = _event_type_values(context_maps)
    has_status_change_metadata = _has_status_change_metadata(event)

    is_direct_status_change = any(value in _STATUS_CHANGE_EVENTS for value in event_types)
    is_status_update = (
        any(value in _ISSUE_UPDATE_EVENTS for value in event_types)
        and has_status_change_metadata
    )
    is_implicit_status_change = not event_types and has_status_change_metadata

    if not (is_direct_status_change or is_status_update or is_implicit_status_change):
        return False

    status = _changed_status(context_maps)
    return _normalize(status) == TARGET_STATUS


def _context_maps(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return maps ordered from broad event context to specific issue data."""
    maps: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in maps:
            maps.append(value)

    add(event)

    automation_info = event.get("automation_trigger_info")
    if isinstance(automation_info, Mapping):
        add(automation_info)
        add(automation_info.get("triggerContext"))

    add(event.get("triggerContext"))
    add(event.get("data"))
    add(event.get("issue"))

    data = event.get("data")
    if isinstance(data, Mapping):
        add(data.get("issue"))
        add(data.get("node"))

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        add(trigger_context.get("issue"))
        add(trigger_context.get("data"))

    return maps


def _event_type_values(context_maps: Iterable[Mapping[str, Any]]) -> set[str]:
    event_keys = ("trigger", "webhookType", "webhook_type", "action", "type", "eventType")
    values: set[str] = set()
    for context in context_maps:
        for key in event_keys:
            value = context.get(key)
            if isinstance(value, str):
                values.add(_normalize(value))
    return values


def _has_status_change_metadata(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized_key = _normalize(key)
            if _is_explicit_new_status_key(key):
                return True
            if normalized_key in {"updatedfields", "updated fields"}:
                if _list_mentions_status(child):
                    return True
            if normalized_key in {"changes", "changed fields", "updatedfrom", "updated from"}:
                if _mapping_mentions_status(child):
                    return True
            if _has_status_change_metadata(child):
                return True
    elif isinstance(value, list):
        return any(_has_status_change_metadata(child) for child in value)
    return False


def _list_mentions_status(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize(value) in _STATUS_FIELD_NAMES
    if isinstance(value, list):
        return any(_list_mentions_status(item) for item in value)
    if isinstance(value, Mapping):
        return _mapping_mentions_status(value)
    return False


def _mapping_mentions_status(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if _normalize(key) in _STATUS_FIELD_NAMES:
                return True
            if _normalize(key) in {"field", "name"} and _list_mentions_status(child):
                return True
            if _mapping_mentions_status(child):
                return True
    if isinstance(value, list):
        return any(_mapping_mentions_status(item) for item in value)
    return False


def _changed_status(context_maps: Iterable[Mapping[str, Any]]) -> str | None:
    explicit = _explicit_new_status(context_maps)
    if explicit:
        return explicit

    changed = _status_from_changes(context_maps)
    if changed:
        return changed

    return _current_status(context_maps)


def _explicit_new_status(context_maps: Iterable[Mapping[str, Any]]) -> str | None:
    for context in context_maps:
        for key in _EXPLICIT_NEW_STATUS_KEYS:
            value = _named_value(context.get(key))
            if value:
                return value
    return None


def _status_from_changes(context_maps: Iterable[Mapping[str, Any]]) -> str | None:
    for context in context_maps:
        for key in ("changes", "changedFields", "changed_fields"):
            changes = context.get(key)
            value = _status_from_change_payload(changes)
            if value:
                return value
    return None


def _status_from_change_payload(value: Any) -> str | None:
    if isinstance(value, Mapping):
        changed_field = value.get("field") or value.get("name")
        if _list_mentions_status(changed_field):
            changed_value = _new_value_from_change(value)
            if changed_value:
                return changed_value

        for key, child in value.items():
            if _normalize(key) in _STATUS_FIELD_NAMES:
                changed_value = _new_value_from_change(child)
                if changed_value:
                    return changed_value
            nested = _status_from_change_payload(child)
            if nested:
                return nested
    elif isinstance(value, list):
        for item in value:
            nested = _status_from_change_payload(item)
            if nested:
                return nested
    return None


def _new_value_from_change(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in (
            "to",
            "new",
            "newValue",
            "new_value",
            "after",
            "current",
            "value",
            "name",
        ):
            named = _named_value(value.get(key))
            if named:
                return named
    return _named_value(value)


def _current_status(context_maps: Iterable[Mapping[str, Any]]) -> str | None:
    for context in context_maps:
        for key in ("status", "state", "workflowState", "workflow_state"):
            value = _named_value(context.get(key))
            if value:
                return value
    return None


def _issue_id(context_maps: Iterable[Mapping[str, Any]]) -> str | None:
    for key in ("issueId", "issue_id", "identifier", "key", "id"):
        for context in reversed(list(context_maps)):
            value = _clean_text(context.get(key))
            if value:
                return value
    return None


def _issue_title(context_maps: Iterable[Mapping[str, Any]]) -> str | None:
    for key in ("title", "name"):
        for context in reversed(list(context_maps)):
            value = _clean_text(context.get(key))
            if value:
                return value
    return None


def _named_value(value: Any) -> str | None:
    if isinstance(value, str):
        return _clean_text(value)
    if isinstance(value, Mapping):
        for key in ("name", "title", "label", "value", "id"):
            named = _clean_text(value.get(key))
            if named:
                return named
    return None


def _clean_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _is_explicit_new_status_key(value: str) -> bool:
    return _normalize(value) in {_normalize(key) for key in _EXPLICIT_NEW_STATUS_KEYS}


def _normalize(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    camel_split = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    words = re.sub(r"[^A-Za-z0-9]+", " ", camel_split).strip().casefold()
    return re.sub(r"\s+", " ", words)


def main() -> int:
    payload = json.load(sys.stdin)
    update = build_issue_title_update(payload)
    if update is not None:
        json.dump(update, sys.stdout, indent=2)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
