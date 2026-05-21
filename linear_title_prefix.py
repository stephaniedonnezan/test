"""Helpers for marking Linear issues when they move into research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_EVENT_KEYS = (
    "trigger",
    "webhookType",
    "webhook_type",
    "action",
    "type",
    "event",
    "eventType",
    "event_type",
)
_EXPLICIT_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "currentStatus",
    "current_status",
    "statusName",
    "status_name",
    "newState",
    "new_state",
    "stateName",
    "state_name",
    "workflowStateName",
    "workflow_state_name",
)
_STATUS_KEYS = ("status", "state", "workflowState", "workflow_state")
_ISSUE_ID_KEYS = ("id", "issueId", "issue_id", "identifier")
_UPDATED_FIELD_KEYS = (
    "updatedFields",
    "updated_fields",
    "changedFields",
    "changed_fields",
)
_UPDATE_EVENTS = {"update", "updated", "issueupdated", "updatedissue"}
_STATUS_CHANGE_EVENTS = {
    "statuschange",
    "statuschanged",
    "statechange",
    "statechanged",
    "workflowstatechange",
    "workflowstatechanged",
}
_STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow_state"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Build a title update action for a Linear status-change event.

    The automation runner can call this function with the Linear/Cursor webhook
    payload. When the payload represents a status change into "to research",
    the function returns a small action dictionary describing the desired issue
    title update. Non-matching payloads return ``None``.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    status = _extract_new_status(event)
    if _normalize_status(status) != _normalize_status(TARGET_STATUS):
        return None

    issue_id, title = _extract_issue_identity(event)
    if not issue_id or not title:
        return None

    if _has_title_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def handle_issue_status_changed(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Backward-compatible alias for automation entry points."""

    return build_issue_title_update(event)


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    event_values = {
        _compact_token(value)
        for mapping in _candidate_event_mappings(event)
        for key in _EVENT_KEYS
        if (value := mapping.get(key)) is not None
    }

    if event_values & _STATUS_CHANGE_EVENTS:
        return True

    if event_values & _UPDATE_EVENTS:
        return _updated_fields_include_status(event)

    return False


def _extract_new_status(event: Mapping[str, Any]) -> str | None:
    candidates = _candidate_issue_mappings(event)

    for mapping in candidates:
        for key in _EXPLICIT_STATUS_KEYS:
            value = mapping.get(key)
            status = _status_value(value)
            if status:
                return status

    for mapping in candidates:
        for key in _STATUS_KEYS:
            value = mapping.get(key)
            status = _status_value(value)
            if status:
                return status

    return None


def _extract_issue_identity(event: Mapping[str, Any]) -> tuple[str | None, str | None]:
    issue_id = None
    title = None

    for mapping in _candidate_issue_mappings(event):
        if issue_id is None:
            issue_id = _first_string(mapping, _ISSUE_ID_KEYS)
        if title is None:
            title = _coerce_string(mapping.get("title"))
        if issue_id and title:
            break

    return issue_id, title


def _candidate_event_mappings(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    mappings = [event]
    for key in ("triggerContext", "trigger_context", "payload", "data"):
        value = event.get(key)
        if isinstance(value, Mapping):
            mappings.append(value)
    return mappings


def _candidate_issue_mappings(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    candidates: list[Mapping[str, Any]] = []

    def add(mapping: Mapping[str, Any] | None) -> None:
        if mapping is not None and mapping not in candidates:
            candidates.append(mapping)

    trigger_context = _mapping_at(event, "triggerContext") or _mapping_at(
        event, "trigger_context"
    )
    payload = _mapping_at(event, "payload")
    data = _mapping_at(event, "data")
    issue = _mapping_at(event, "issue")
    payload_issue = _mapping_at(payload, "issue") if payload is not None else None
    data_issue = _mapping_at(data, "issue") if data is not None else None

    add(trigger_context)
    add(issue)
    add(payload_issue)
    add(data_issue)
    add(data)
    add(payload)
    add(event)

    return candidates


def _updated_fields_include_status(event: Mapping[str, Any]) -> bool:
    for mapping in _walk_mappings(event):
        for key in _UPDATED_FIELD_KEYS:
            if _field_names_include_status(mapping.get(key)):
                return True

        updated_from = mapping.get("updatedFrom") or mapping.get("updated_from")
        if isinstance(updated_from, Mapping) and any(
            _compact_token(key) in _STATUS_FIELD_NAMES for key in updated_from
        ):
            return True

    return False


def _field_names_include_status(value: Any) -> bool:
    if isinstance(value, str):
        return _compact_token(value) in _STATUS_FIELD_NAMES

    if isinstance(value, Mapping):
        return any(_compact_token(key) in _STATUS_FIELD_NAMES for key in value)

    if isinstance(value, Iterable):
        return any(_field_names_include_status(item) for item in value)

    return False


def _walk_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for nested in value.values():
            yield from _walk_mappings(nested)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_mappings(item)


def _mapping_at(mapping: Mapping[str, Any] | None, key: str) -> Mapping[str, Any] | None:
    if mapping is None:
        return None

    value = mapping.get(key)
    return value if isinstance(value, Mapping) else None


def _first_string(mapping: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for key in keys:
        value = _coerce_string(mapping.get(key))
        if value:
            return value
    return None


def _status_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        return _first_string(value, ("name", "title", "label", "id"))
    return _coerce_string(value)


def _coerce_string(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _has_title_prefix(title: str) -> bool:
    return title.strip().lower().startswith(TITLE_PREFIX.lower())


def _normalize_status(status: str | None) -> str | None:
    if status is None:
        return None

    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", status)
    spaced = re.sub(r"[^a-zA-Z0-9]+", " ", spaced)
    return re.sub(r"\s+", " ", spaced).strip().lower()


def _compact_token(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    normalized = _normalize_status(value)
    return normalized.replace(" ", "") if normalized is not None else ""


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
