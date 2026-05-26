"""Build Linear issue title updates for research-status automation events."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "stateid",
    "statename",
    "workflowstate",
    "workflowstateid",
    "workflowstatename",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to To Research.

    The automation trigger can arrive either as a flat ``triggerContext`` payload
    or in a nested Linear webhook shape. The returned dictionary is intentionally
    small so the caller can pass it to whatever Linear client performs updates.
    """

    if not isinstance(event, Mapping):
        return None

    maps = _context_maps(event)
    if not _is_status_change_event(maps):
        return None

    status = _extract_new_status(maps)
    if _normalize_text(status) != TARGET_STATUS:
        return None

    issue_id = _extract_issue_id(maps)
    title = _extract_title(maps)
    if issue_id is None or title is None:
        return None

    clean_title = title.strip()
    if not clean_title or _has_research_prefix(clean_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {clean_title}",
    }


def _context_maps(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    maps: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and not any(value is existing for existing in maps):
            maps.append(value)

    trigger_context = event.get("triggerContext")
    data = event.get("data")
    issue = event.get("issue")

    add(trigger_context)
    if isinstance(trigger_context, Mapping):
        add(trigger_context.get("data"))
        add(trigger_context.get("issue"))
        trigger_data = trigger_context.get("data")
        if isinstance(trigger_data, Mapping):
            add(trigger_data.get("issue"))

    if isinstance(data, Mapping):
        add(data.get("issue"))
    add(issue)
    add(data)
    add(event)

    return maps


def _is_status_change_event(maps: Iterable[Mapping[str, Any]]) -> bool:
    saw_update_event = False
    saw_status_field_change = False

    for mapping in maps:
        for key in ("trigger", "webhookType", "action", "type", "event", "eventType"):
            value = _string_value(mapping.get(key))
            if value is None:
                continue

            normalized = _normalize_text(value)
            if normalized in {
                "status changed",
                "status change",
                "state changed",
                "state change",
                "workflow state changed",
                "workflow state change",
            }:
                return True

            if normalized in {
                "update",
                "updated",
                "issue update",
                "issue updated",
                "updated issue",
            }:
                saw_update_event = True

        if _changed_fields_include_status(mapping):
            saw_status_field_change = True

    return saw_update_event and saw_status_field_change


def _changed_fields_include_status(mapping: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        fields = mapping.get(key)
        if _field_names_include_status(fields):
            return True

    updated_from = mapping.get("updatedFrom")
    if isinstance(updated_from, Mapping):
        return _field_names_include_status(updated_from.keys())

    changes = mapping.get("changes")
    if isinstance(changes, Mapping):
        return _field_names_include_status(changes.keys())
    if isinstance(changes, list):
        return any(_field_names_include_status(change) for change in changes)

    return False


def _field_names_include_status(fields: Any) -> bool:
    if isinstance(fields, Mapping):
        field_iterable = fields.keys()
    elif isinstance(fields, str):
        field_iterable = (fields,)
    elif isinstance(fields, Iterable):
        field_iterable = fields
    else:
        return False

    for field in field_iterable:
        normalized = _normalize_key(field)
        if normalized in _STATUS_FIELD_NAMES:
            return True

    return False


def _extract_new_status(maps: Iterable[Mapping[str, Any]]) -> str | None:
    direct_keys = (
        "newStatus",
        "new_status",
        "statusName",
        "status_name",
        "newState",
        "new_state",
        "stateName",
        "state_name",
        "workflowStateName",
        "workflow_state_name",
    )
    nested_keys = ("status", "state", "workflowState", "workflow_state")

    for mapping in maps:
        for key in direct_keys:
            value = _string_value(mapping.get(key))
            if value is not None:
                return value

    for mapping in maps:
        for key in nested_keys:
            value = mapping.get(key)
            status = _string_value(value)
            if status is not None:
                return status
            if isinstance(value, Mapping):
                nested_status = _string_value(value.get("name")) or _string_value(
                    value.get("title")
                )
                if nested_status is not None:
                    return nested_status

    return None


def _extract_issue_id(maps: Iterable[Mapping[str, Any]]) -> str | None:
    for mapping in maps:
        for key in ("issueId", "issue_id", "identifier", "id"):
            value = _string_value(mapping.get(key))
            if value is not None and value.strip():
                return value.strip()

    return None


def _extract_title(maps: Iterable[Mapping[str, Any]]) -> str | None:
    for mapping in maps:
        value = _string_value(mapping.get("title"))
        if value is not None:
            return value

    return None


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(TITLE_PREFIX.casefold())


def _string_value(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    return None


def _normalize_text(value: Any) -> str:
    string_value = _string_value(value)
    if string_value is None:
        return ""

    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", string_value.strip())
    spaced = re.sub(r"[^A-Za-z0-9]+", " ", spaced)
    return " ".join(spaced.casefold().split())


def _normalize_key(value: Any) -> str:
    string_value = _string_value(value)
    if string_value is None:
        return ""

    return re.sub(r"[^A-Za-z0-9]+", "", string_value).casefold()


def main() -> int:
    payload = json.load(sys.stdin)
    result = build_issue_title_update(payload)
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
