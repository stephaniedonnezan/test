"""Build Linear issue title updates for research-status automation."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping, Sequence
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_DIRECT_STATUS_CHANGE_EVENTS = {
    "statuschange",
    "statuschanged",
    "statechange",
    "statechanged",
    "workflowstatechange",
    "workflowstatechanged",
}
_GENERIC_UPDATE_EVENTS = {
    "update",
    "updated",
    "issueupdate",
    "issueupdated",
    "updatedissue",
}
_STATUS_FIELD_NAMES = {
    "status",
    "statusid",
    "state",
    "stateid",
    "workflowstate",
    "workflowstateid",
    "workflowstatus",
    "workflowstatusid",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue-title update action when a Linear issue moves to research.

    The function is intentionally side-effect free. Callers can decide how to apply
    the returned action to Linear.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    if not _is_target_status(_extract_new_status(event)):
        return None

    issue_id = _extract_issue_id(event)
    title = _extract_title(event)
    if not issue_id or not title:
        return None

    clean_title = title.strip()
    if not clean_title or clean_title.lower().startswith(TITLE_PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {clean_title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    has_generic_update = False

    for mapping in _all_mappings(event):
        for key in ("trigger", "webhookType", "action", "type", "eventType"):
            value = mapping.get(key)
            if not isinstance(value, str):
                continue

            normalized = _normalize_words(value)
            compact = normalized.replace(" ", "")
            if compact in _DIRECT_STATUS_CHANGE_EVENTS:
                return True

            if compact in _GENERIC_UPDATE_EVENTS:
                has_generic_update = True

    return has_generic_update and _mentions_status_field(event)


def _extract_new_status(event: Mapping[str, Any]) -> str | None:
    for mapping in _priority_mappings(event):
        status = _first_status_value(
            mapping,
            (
                "newStatus",
                "new_status",
                "newState",
                "new_state",
                "newWorkflowState",
                "new_workflow_state",
                "targetStatus",
                "target_status",
            ),
        )
        if status:
            return status

    for mapping in _priority_mappings(event):
        status = _status_from_changes(mapping.get("changes"))
        if status:
            return status

    for mapping in _priority_mappings(event):
        status = _first_status_value(
            mapping,
            (
                "status",
                "state",
                "workflowState",
                "workflow_state",
                "workflowStatus",
                "workflow_status",
            ),
        )
        if status:
            return status

    return None


def _extract_issue_id(event: Mapping[str, Any]) -> str | None:
    for mapping in _priority_mappings(event):
        for key in ("issueId", "issue_id", "identifier", "key", "id"):
            value = mapping.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _extract_title(event: Mapping[str, Any]) -> str | None:
    for mapping in _priority_mappings(event):
        value = mapping.get("title")
        if isinstance(value, str) and value.strip():
            return value
    return None


def _priority_mappings(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    mappings: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and not any(value is existing for existing in mappings):
            mappings.append(value)

    trigger_context = event.get("triggerContext")
    add(trigger_context)
    add(_get_mapping(trigger_context, "data", "issue"))
    add(_get_mapping(trigger_context, "issue"))
    add(_get_mapping(trigger_context, "data"))

    add(_get_mapping(event, "data", "issue"))
    add(_get_mapping(event, "issue"))
    add(_get_mapping(event, "data"))
    add(event)

    for mapping in _all_mappings(event):
        add(mapping)

    return mappings


def _all_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if not isinstance(value, Mapping):
        return

    yield value
    for nested in value.values():
        if isinstance(nested, Mapping):
            yield from _all_mappings(nested)
        elif _is_sequence(nested):
            for item in nested:
                yield from _all_mappings(item)


def _get_mapping(value: Any, *path: str) -> Mapping[str, Any] | None:
    current = value
    for key in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current if isinstance(current, Mapping) else None


def _first_status_value(mapping: Mapping[str, Any], keys: Sequence[str]) -> str | None:
    for key in keys:
        status = _string_from_status_value(mapping.get(key))
        if status:
            return status
    return None


def _status_from_changes(value: Any) -> str | None:
    if not isinstance(value, Mapping):
        return None

    for field_name, change in value.items():
        if not _is_status_field(field_name):
            continue

        status = _string_from_status_value(change, prefer_transition_target=True)
        if status:
            return status

    return None


def _string_from_status_value(value: Any, *, prefer_transition_target: bool = False) -> str | None:
    if isinstance(value, str):
        return value.strip() or None

    if not isinstance(value, Mapping):
        return None

    keys = (
        ("to", "after", "new", "newValue", "new_value", "current", "name", "displayName")
        if prefer_transition_target
        else ("name", "displayName", "status", "state", "workflowState", "value")
    )
    for key in keys:
        nested = _string_from_status_value(value.get(key))
        if nested:
            return nested

    return None


def _mentions_status_field(event: Mapping[str, Any]) -> bool:
    for mapping in _all_mappings(event):
        for key in (
            "updatedFields",
            "updated_fields",
            "changedFields",
            "changed_fields",
            "updatedField",
            "changedField",
            "changes",
            "updatedFrom",
            "updated_from",
        ):
            if any(_is_status_field(field_name) for field_name in _field_names(mapping.get(key))):
                return True
    return False


def _field_names(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
        return

    if isinstance(value, Mapping):
        for key in value:
            if isinstance(key, str):
                yield key
        for key in ("field", "fieldName", "field_name", "name", "key"):
            nested = value.get(key)
            if isinstance(nested, str):
                yield nested
        return

    if _is_sequence(value):
        for item in value:
            yield from _field_names(item)


def _is_status_field(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    return _normalize_words(value).replace(" ", "") in _STATUS_FIELD_NAMES


def _is_target_status(value: str | None) -> bool:
    if value is None:
        return False
    return _normalize_words(value) == TARGET_STATUS


def _normalize_words(value: str) -> str:
    words = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value.strip())
    words = re.sub(r"[^A-Za-z0-9]+", " ", words)
    return re.sub(r"\s+", " ", words).strip().lower()


def _is_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    update = build_issue_title_update(event)
    json.dump(update, sys.stdout, indent=2, sort_keys=True)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
