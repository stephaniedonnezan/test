"""Build Linear issue title updates for Cursor research status automations."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow"}
DIRECT_STATUS_CHANGE_TRIGGERS = {
    "status changed",
    "status change",
    "status updated",
    "state changed",
    "state change",
    "workflow state changed",
}
GENERIC_UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return the title update action for a Linear issue moved to To Research.

    The Cursor automation trigger provides a flat ``triggerContext`` payload, while
    Linear webhooks can nest issue details under ``data`` or ``issue``. This
    function accepts both shapes and returns ``None`` when no title update is
    needed.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    status = _new_status(event)
    if _normalize_text(status) != TARGET_STATUS:
        return None

    title = _issue_title(event)
    if title is None or _has_prefix(title):
        return None

    issue_id = _issue_id(event)
    if issue_id is None:
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    trigger_values = {
        _normalize_text(value)
        for mapping in _walk_mappings(event)
        for key, value in mapping.items()
        if _normalize_key(key) in {"trigger", "webhooktype", "action", "type", "event"}
        and isinstance(value, str)
    }

    if trigger_values & DIRECT_STATUS_CHANGE_TRIGGERS:
        return True

    if trigger_values & GENERIC_UPDATE_TRIGGERS:
        return _status_field_changed(event)

    return False


def _status_field_changed(event: Mapping[str, Any]) -> bool:
    change_keys = {
        "changes",
        "change",
        "changedfields",
        "changedfield",
        "updatedfields",
        "updatedfield",
        "updatedfrom",
        "updated_from",
    }

    for mapping in _walk_mappings(event):
        for key, value in mapping.items():
            if _normalize_key(key) not in change_keys:
                continue
            if _contains_status_field_reference(value):
                return True
    return False


def _contains_status_field_reference(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field_name(value)

    if isinstance(value, Mapping):
        return any(
            _is_status_field_name(key) or _contains_status_field_reference(child)
            for key, child in value.items()
        )

    if _is_non_string_sequence(value):
        return any(_contains_status_field_reference(item) for item in value)

    return False


def _new_status(event: Mapping[str, Any]) -> str | None:
    for status in _status_from_changes(event):
        if status:
            return status

    explicit_keys = (
        "newstatus",
        "newstate",
        "newworkflowstate",
        "statusname",
        "statustitle",
        "statustype",
        "statename",
        "workflowstatename",
    )
    fallback_keys = ("status", "state", "workflowstate")

    for mapping in _candidate_issue_maps(event):
        for key in explicit_keys:
            status = _string_or_name(_value_for_normalized_key(mapping, key))
            if status:
                return status

    for mapping in _candidate_issue_maps(event):
        for key in fallback_keys:
            status = _string_or_name(_value_for_normalized_key(mapping, key))
            if status:
                return status

    return None


def _status_from_changes(event: Mapping[str, Any]) -> list[str]:
    statuses: list[str] = []
    change_keys = {"changes", "change", "updatedfields", "updated_fields"}

    for mapping in _walk_mappings(event):
        for key, value in mapping.items():
            if _normalize_key(key) not in change_keys:
                continue
            statuses.extend(_extract_statuses_from_change_value(value))

    return statuses


def _extract_statuses_from_change_value(value: Any) -> list[str]:
    if isinstance(value, Mapping):
        statuses: list[str] = []
        for key, child in value.items():
            if _is_status_field_name(key):
                status = _new_value_from_change(child)
                if status:
                    statuses.append(status)
            elif _normalize_key(key) in {"to", "new", "after", "current"}:
                status = _string_or_name(child)
                if status:
                    statuses.append(status)
            else:
                statuses.extend(_extract_statuses_from_change_value(child))
        return statuses

    if _is_non_string_sequence(value):
        return [
            status
            for item in value
            for status in _extract_statuses_from_change_value(item)
        ]

    return []


def _new_value_from_change(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("to", "new", "after", "current", "name"):
            if key in value:
                status = _string_or_name(value[key])
                if status:
                    return status
    return _string_or_name(value)


def _issue_title(event: Mapping[str, Any]) -> str | None:
    for mapping in _candidate_issue_maps(event):
        title = mapping.get("title")
        if isinstance(title, str):
            trimmed = title.strip()
            if trimmed:
                return trimmed
    return None


def _issue_id(event: Mapping[str, Any]) -> str | None:
    id_keys = ("id", "issueid", "issue_id", "identifier", "key")

    for mapping in _candidate_issue_maps(event):
        for key in id_keys:
            issue_id = _value_for_normalized_key(mapping, key)
            if isinstance(issue_id, str) and issue_id.strip():
                return issue_id.strip()
    return None


def _candidate_issue_maps(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return likely issue payloads before outer webhook metadata."""

    candidates: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and not any(value is item for item in candidates):
            candidates.append(value)

    trigger_context = event.get("triggerContext")
    add(trigger_context)

    data = event.get("data")
    if isinstance(data, Mapping):
        add(data.get("issue"))
        add(data)

    add(event.get("issue"))
    add(event.get("node"))
    add(event)

    return candidates


def _walk_mappings(value: Any) -> list[Mapping[str, Any]]:
    mappings: list[Mapping[str, Any]] = []

    def walk(child: Any) -> None:
        if isinstance(child, Mapping):
            mappings.append(child)
            for nested in child.values():
                walk(nested)
        elif _is_non_string_sequence(child):
            for nested in child:
                walk(nested)

    walk(value)
    return mappings


def _string_or_name(value: Any) -> str | None:
    if isinstance(value, str):
        trimmed = value.strip()
        return trimmed or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            child = value.get(key)
            if isinstance(child, str) and child.strip():
                return child.strip()

    return None


def _value_for_normalized_key(mapping: Mapping[str, Any], normalized_key: str) -> Any:
    for key, value in mapping.items():
        if _normalize_key(key) == _normalize_key(normalized_key):
            return value
    return None


def _has_prefix(title: str) -> bool:
    return title.lstrip().lower().startswith(PREFIX.lower())


def _is_status_field_name(value: Any) -> bool:
    if not isinstance(value, str):
        return False

    normalized = _normalize_key(value)
    return any(normalized == name or normalized.startswith(f"{name}id") for name in STATUS_FIELD_NAMES)


def _normalize_key(value: Any) -> str:
    return _normalize_text(value).replace(" ", "")


def _normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    normalized = re.sub(r"[^A-Za-z0-9]+", " ", spaced).strip().lower()
    return re.sub(r"\s+", " ", normalized)


def _is_non_string_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
