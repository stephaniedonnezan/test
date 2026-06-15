"""Build Linear issue title updates for research-status automation."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_DIRECT_STATUS_CHANGE_MARKERS = {
    "issue status changed",
    "status changed",
    "status change",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
}
_GENERIC_UPDATE_MARKERS = {
    "issue updated",
    "updated issue",
    "update",
    "updated",
}
_STATUS_FIELD_MARKERS = {
    "status",
    "state",
    "state id",
    "workflow state",
    "workflow state id",
}
_EVENT_MARKER_KEYS = {"trigger", "webhookType", "action", "type", "event", "name"}
_EXPLICIT_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "newWorkflowState",
    "new_workflow_state",
    "toStatus",
    "to_status",
    "statusName",
    "status_name",
    "stateName",
    "state_name",
    "workflowStateName",
    "workflow_state_name",
)
_CURRENT_STATUS_KEYS = ("status", "state", "workflowState", "workflow_state")
_ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "key", "id")
_TITLE_KEYS = ("title", "name")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear issue title update action for "to research" status changes."""
    if not isinstance(event, Mapping):
        return None

    candidates = list(_candidate_mappings(event))
    if not _is_status_change_event(event):
        return None

    status = _find_status(candidates)
    if _normalize_text(status) != TARGET_STATUS:
        return None

    issue_id = _find_string(candidates, _ISSUE_ID_KEYS)
    title = _find_string(candidates, _TITLE_KEYS)
    if not issue_id or not title:
        return None

    title = title.strip()
    if not title or title.lower().startswith(TITLE_PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _candidate_mappings(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely issue/context mappings from outermost automation payloads."""
    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        yield trigger_context

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            yield issue
        yield data

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        yield issue

    yield event


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    markers = {_normalize_text(value) for value in _event_marker_values(event)}
    markers.discard("")

    if markers & _DIRECT_STATUS_CHANGE_MARKERS:
        return True

    if markers & _GENERIC_UPDATE_MARKERS:
        return _has_status_field_marker(event)

    return False


def _event_marker_values(value: Any) -> Iterable[Any]:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if key in _EVENT_MARKER_KEYS:
                yield child
            if isinstance(child, Mapping | list | tuple):
                yield from _event_marker_values(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from _event_marker_values(child)


def _has_status_field_marker(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized_key = _normalize_text(key)
            if normalized_key in {
                "updated fields",
                "changed fields",
                "changes",
                "changed",
                "updated from",
                "previous values",
            }:
                if _contains_status_field(child):
                    return True
            if isinstance(child, Mapping | list | tuple) and _has_status_field_marker(child):
                return True
    elif isinstance(value, (list, tuple)):
        return any(_has_status_field_marker(child) for child in value)

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)

    if isinstance(value, Mapping):
        return any(_is_status_field(key) or _contains_status_field(child) for key, child in value.items())

    if isinstance(value, (list, tuple, set)):
        return any(_contains_status_field(child) for child in value)

    return False


def _is_status_field(value: Any) -> bool:
    normalized = _normalize_text(value)
    return normalized in _STATUS_FIELD_MARKERS


def _find_status(candidates: Iterable[Mapping[str, Any]]) -> str | None:
    candidates = list(candidates)

    for candidate in candidates:
        value = _find_field(candidate, _EXPLICIT_STATUS_KEYS)
        status = _status_value(value)
        if status:
            return status

    for candidate in candidates:
        value = _find_field(candidate, _CURRENT_STATUS_KEYS)
        status = _status_value(value)
        if status:
            return status

    return None


def _find_string(candidates: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for candidate in candidates:
        value = _find_field(candidate, keys)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _find_field(mapping: Mapping[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        if key in mapping:
            return mapping[key]
    return None


def _status_value(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value

    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            nested = value.get(key)
            if isinstance(nested, str) and nested.strip():
                return nested

    return None


def _normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value.strip())
    words = re.sub(r"[^A-Za-z0-9]+", " ", spaced).lower().split()
    return " ".join(words)


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON input: {exc}", file=sys.stderr)
        return 1

    result = build_issue_title_update(event)
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
