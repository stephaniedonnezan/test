"""Build Linear issue title update actions for research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


ACTION = "update_issue_title"
PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_DIRECT_STATUS_CHANGE_EVENTS = {
    "status changed",
    "status change",
    "state changed",
    "workflow state changed",
    "workflow status changed",
}
_GENERIC_UPDATE_EVENTS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}
_STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow state"}
_EVENT_KEYS = {"trigger", "webhookType", "eventType", "type", "action"}
_EXPLICIT_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "toStatus",
    "statusName",
    "newState",
    "new_state",
    "toState",
    "stateName",
    "workflowState",
    "workflowStateName",
)
_ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "key", "id")


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to research."""

    if not isinstance(event, Mapping):
        return None

    records = list(_candidate_records(event))
    if not _is_status_change_event(records):
        return None

    new_status = _extract_new_status(records)
    if _normalize_status(new_status) != TARGET_STATUS:
        return None

    issue_id = _extract_issue_id(records)
    title = _extract_title(records)
    if not issue_id or not title:
        return None

    if _has_research_prefix(title):
        next_title = title
    else:
        next_title = f"{PREFIX}: {title}"

    return {"action": ACTION, "issueId": issue_id, "title": next_title}


def _candidate_records(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely metadata and issue records in precedence order."""

    yield from _mapping_at_path(event, ("automation_trigger_info", "triggerContext"))
    yield from _mapping_at_path(event, ("triggerContext",))
    yield event
    yield from _mapping_at_path(event, ("data", "issue"))
    yield from _mapping_at_path(event, ("payload", "issue"))
    yield from _mapping_at_path(event, ("issue",))
    yield from _mapping_at_path(event, ("data",))
    yield from _mapping_at_path(event, ("payload",))


def _mapping_at_path(root: Mapping[str, Any], path: tuple[str, ...]) -> Iterable[Mapping[str, Any]]:
    current: Any = root
    for key in path:
        if not isinstance(current, Mapping):
            return
        current = current.get(key)
    if isinstance(current, Mapping):
        yield current


def _is_status_change_event(records: list[Mapping[str, Any]]) -> bool:
    if _has_direct_status_change_event(records):
        return True

    if _has_generic_update_event(records) and _has_status_change_marker(records):
        return True

    return False


def _has_direct_status_change_event(records: list[Mapping[str, Any]]) -> bool:
    for value in _event_values(records):
        normalized = _normalize_label(value)
        if normalized in _DIRECT_STATUS_CHANGE_EVENTS:
            return True
    return False


def _has_generic_update_event(records: list[Mapping[str, Any]]) -> bool:
    for value in _event_values(records):
        normalized = _normalize_label(value)
        if normalized in _GENERIC_UPDATE_EVENTS:
            return True
    return False


def _event_values(records: list[Mapping[str, Any]]) -> Iterable[Any]:
    for record in records:
        for key, value in record.items():
            if key in _EVENT_KEYS:
                yield value


def _has_status_change_marker(records: list[Mapping[str, Any]]) -> bool:
    for record in records:
        for key in ("updatedFields", "changedFields", "fields"):
            if _contains_status_field(record.get(key)):
                return True

        changes = record.get("changes")
        if _changes_include_status(changes):
            return True

        updated_from = record.get("updatedFrom")
        if _contains_status_field(updated_from) or _changes_include_status(updated_from):
            return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_field_name(value) in _STATUS_FIELD_NAMES

    if isinstance(value, Mapping):
        return any(_contains_status_field(key) for key in value.keys())

    if isinstance(value, Iterable):
        return any(_contains_status_field(item) for item in value)

    return False


def _changes_include_status(changes: Any) -> bool:
    if not isinstance(changes, Mapping):
        return False

    for key, value in changes.items():
        if _contains_status_field(key):
            return True
        if isinstance(value, Mapping) and _contains_status_field(value.get("field")):
            return True

    return False


def _extract_new_status(records: list[Mapping[str, Any]]) -> str | None:
    for record in records:
        for key in _EXPLICIT_STATUS_KEYS:
            value = _string_or_name(record.get(key))
            if value:
                return value

    for record in records:
        value = _status_from_changes(record.get("changes"))
        if value:
            return value

        value = _status_from_changes(record.get("updatedFrom"), prefer_current=False)
        if value:
            return value

    for record in records:
        for key in ("status", "state", "workflowState"):
            value = _string_or_name(record.get(key))
            if value:
                return value

    return None


def _status_from_changes(changes: Any, prefer_current: bool = True) -> str | None:
    if not isinstance(changes, Mapping):
        return None

    for key, value in changes.items():
        if _contains_status_field(key):
            extracted = _new_change_value(value, prefer_current)
            if extracted:
                return extracted
        if isinstance(value, Mapping) and _contains_status_field(value.get("field")):
            extracted = _new_change_value(value, prefer_current)
            if extracted:
                return extracted

    return None


def _new_change_value(value: Any, prefer_current: bool) -> str | None:
    if not isinstance(value, Mapping):
        return _string_or_name(value)

    preferred_keys = ("new", "to", "newValue", "toValue", "after", "current")
    fallback_keys = ("from", "old", "oldValue", "previous")
    keys = preferred_keys if prefer_current else preferred_keys + fallback_keys
    for key in keys:
        extracted = _string_or_name(value.get(key))
        if extracted:
            return extracted

    return _string_or_name(value)


def _extract_issue_id(records: list[Mapping[str, Any]]) -> str | None:
    for key in _ISSUE_ID_KEYS:
        for record in records:
            value = record.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _extract_title(records: list[Mapping[str, Any]]) -> str | None:
    for record in records:
        value = record.get("title")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _string_or_name(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            nested = value.get(key)
            if isinstance(nested, str) and nested.strip():
                return nested.strip()

    return None


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())


def _normalize_status(value: str | None) -> str | None:
    if value is None:
        return None
    return _normalize_label(value)


def _normalize_label(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value.strip())
    normalized = re.sub(r"[^A-Za-z0-9]+", " ", spaced)
    return re.sub(r"\s+", " ", normalized).strip().casefold()


def _normalize_field_name(value: Any) -> str:
    return _normalize_label(value).replace(" ", "")


def main() -> int:
    payload = json.load(sys.stdin)
    result = build_issue_title_update(payload)
    if result is not None:
        json.dump(result, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
