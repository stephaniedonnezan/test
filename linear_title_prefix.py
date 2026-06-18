"""Build title update actions for Linear issues entering research.

The automation that calls this module is expected to pass a Linear/Cursor
webhook payload.  When the payload represents an issue status change to
``To Research``, ``build_issue_title_update`` returns the title update action
needed by the caller.  Other payloads return ``None``.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_CONTAINER_KEYS = (
    "triggerContext",
    "trigger_context",
    "payload",
    "data",
    "issue",
    "node",
    "object",
)
_EVENT_KEYS = ("trigger", "event", "eventType", "event_type", "type", "action", "webhookType")
_DIRECT_STATUS_TRIGGERS = {
    "status changed",
    "status change",
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
    "issue update",
}
_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflow state",
    "workflowstate",
    "status id",
    "state id",
    "workflow state id",
}
_EXPLICIT_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "toStatus",
    "to_status",
    "targetStatus",
    "target_status",
    "statusName",
    "status_name",
    "stateName",
    "state_name",
    "workflowStateName",
    "workflow_state_name",
)
_STATUS_VALUE_KEYS = ("status", "state", "workflowState", "workflow_state")
_CHANGE_KEYS = (
    "changes",
    "change",
    "changedFields",
    "changed_fields",
    "updatedFields",
    "updated_fields",
)
_CHANGE_TO_KEYS = ("to", "after", "new", "newValue", "new_value", "current", "value")
_CHANGE_FIELD_KEYS = ("field", "name", "fieldName", "field_name", "key")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue enters research.

    The function accepts both the flat Cursor automation trigger context and
    nested Linear issue webhook payloads.  It is intentionally side-effect free:
    callers can decide how to apply the returned action.
    """

    if not isinstance(event, Mapping):
        return None

    candidates = list(_mapping_candidates(event))
    if not _is_status_change_event(candidates):
        return None

    new_status = _extract_new_status(candidates)
    if _normalize(new_status) != TARGET_STATUS:
        return None

    issue_id = _extract_issue_id(candidates)
    title = _extract_title(candidates)
    if not issue_id or not title:
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": _with_research_prefix(title),
    }


def _mapping_candidates(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield event mappings from outermost to nested payload containers."""

    seen: set[int] = set()
    stack: list[Mapping[str, Any]] = [event]

    while stack:
        current = stack.pop(0)
        current_id = id(current)
        if current_id in seen:
            continue

        seen.add(current_id)
        yield current

        for key in _CONTAINER_KEYS:
            nested = current.get(key)
            if isinstance(nested, Mapping):
                stack.append(nested)


def _is_status_change_event(candidates: Iterable[Mapping[str, Any]]) -> bool:
    event_names = {
        _normalize(candidate.get(key))
        for candidate in candidates
        for key in _EVENT_KEYS
        if candidate.get(key) is not None
    }
    if event_names & _DIRECT_STATUS_TRIGGERS:
        return True

    if event_names & _GENERIC_UPDATE_EVENTS:
        return any(_has_status_change_metadata(candidate) for candidate in candidates)

    return False


def _has_status_change_metadata(candidate: Mapping[str, Any]) -> bool:
    for key in _CHANGE_KEYS:
        value = candidate.get(key)
        if _change_value_mentions_status(value):
            return True

    return False


def _change_value_mentions_status(value: Any) -> bool:
    if isinstance(value, Mapping):
        if any(_is_status_field(field_name) for field_name in value):
            return True

        field_name = _first_present(value, _CHANGE_FIELD_KEYS)
        if field_name is not None and _is_status_field(field_name):
            return True

        return any(_change_value_mentions_status(nested) for nested in value.values())

    if isinstance(value, list | tuple | set):
        return any(_change_value_mentions_status(item) for item in value)

    return _is_status_field(value)


def _extract_new_status(candidates: Iterable[Mapping[str, Any]]) -> Any:
    for candidate in candidates:
        value = _first_present(candidate, _EXPLICIT_STATUS_KEYS)
        if value is not None:
            return _status_name(value)

    for candidate in candidates:
        value = _status_from_change_metadata(candidate)
        if value is not None:
            return value

    for candidate in candidates:
        for key in _STATUS_VALUE_KEYS:
            value = candidate.get(key)
            if value is not None:
                return _status_name(value)

    return None


def _status_from_change_metadata(candidate: Mapping[str, Any]) -> Any:
    for key in _CHANGE_KEYS:
        value = candidate.get(key)
        extracted = _status_from_change_value(value)
        if extracted is not None:
            return extracted

    return None


def _status_from_change_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        for field_name, change in value.items():
            if _is_status_field(field_name):
                return _status_from_change_item(change)

        field_name = _first_present(value, _CHANGE_FIELD_KEYS)
        if field_name is not None and _is_status_field(field_name):
            return _status_from_change_item(value)

        for nested in value.values():
            extracted = _status_from_change_value(nested)
            if extracted is not None:
                return extracted

    if isinstance(value, list | tuple):
        for item in value:
            extracted = _status_from_change_value(item)
            if extracted is not None:
                return extracted

    return None


def _status_from_change_item(value: Any) -> Any:
    if isinstance(value, Mapping):
        for key in _CHANGE_TO_KEYS:
            if key in value:
                return _status_name(value[key])

        value = _first_present(value, _EXPLICIT_STATUS_KEYS + _STATUS_VALUE_KEYS)
        if value is not None:
            return _status_name(value)

    return _status_name(value)


def _status_name(value: Any) -> Any:
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            if key in value:
                return value[key]

    return value


def _extract_issue_id(candidates: Iterable[Mapping[str, Any]]) -> str | None:
    for keys in (("issueId", "issue_id"), ("identifier", "key"), ("id",)):
        for candidate in candidates:
            value = _first_present(candidate, keys)
            if value is not None and str(value).strip():
                return str(value).strip()

    return None


def _extract_title(candidates: Iterable[Mapping[str, Any]]) -> str | None:
    for candidate in candidates:
        value = candidate.get("title")
        if value is not None and str(value).strip():
            return str(value).strip()

    return None


def _with_research_prefix(title: str) -> str:
    title = title.strip()
    if re.match(r"^cursor\s+researching\b", title, re.IGNORECASE):
        return title

    return f"{TITLE_PREFIX}: {title}"


def _is_status_field(value: Any) -> bool:
    normalized = _normalize(value)
    return normalized in _STATUS_FIELD_NAMES


def _normalize(value: Any) -> str:
    if value is None:
        return ""

    text = str(value).strip()
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[_\-/]+", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def _first_present(mapping: Mapping[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        if key in mapping:
            return mapping[key]

    return None


def main() -> int:
    payload = json.load(sys.stdin)
    update = build_issue_title_update(payload)
    if update is not None:
        json.dump(update, sys.stdout, sort_keys=True)
        sys.stdout.write("\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
