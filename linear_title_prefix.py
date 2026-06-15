"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "toresearch"

STATUS_FIELDS = {
    "status",
    "state",
    "workflowstate",
    "workflowstatus",
}

DIRECT_STATUS_CHANGE_EVENTS = {
    "statuschanged",
    "statuschange",
    "statechanged",
    "statechange",
    "workflowstatechanged",
    "workflowstatechange",
}

GENERIC_UPDATE_EVENTS = {
    "issueupdated",
    "updatedissue",
    "update",
    "updated",
}

EXPLICIT_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "newWorkflowState",
    "new_workflow_state",
    "newWorkflowStateName",
    "new_status_name",
    "statusName",
    "stateName",
)

CURRENT_STATUS_KEYS = (
    "status",
    "state",
    "workflowState",
    "workflow_state",
    "workflowStatus",
    "workflow_status",
)

ID_KEYS = ("issueId", "issue_id", "identifier", "key", "id")
TITLE_KEYS = ("title", "issueTitle", "issue_title", "name")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue title update action when a Linear issue enters research.

    The Cursor automation payload is flat under ``triggerContext`` while raw
    Linear webhook payloads are usually nested under ``data.issue``. This helper
    accepts both forms and returns a serializable action only when the event is a
    status/state change whose destination status is "to research".
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_research_status_change(event):
        return None

    issue_id = _first_text(_issue_sources(event), ID_KEYS)
    title = _first_text(_issue_sources(event), TITLE_KEYS)
    if not issue_id or not title:
        return None

    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _is_research_status_change(event: Mapping[str, Any]) -> bool:
    if not _looks_like_status_change_event(event):
        return False

    status = _target_status(event)
    return _normalize(status) == TARGET_STATUS


def _looks_like_status_change_event(event: Mapping[str, Any]) -> bool:
    event_names = [_normalize(value) for value in _event_name_values(event)]

    if any(name in DIRECT_STATUS_CHANGE_EVENTS for name in event_names):
        return True

    return any(name in GENERIC_UPDATE_EVENTS for name in event_names) and _status_field_changed(event)


def _target_status(event: Mapping[str, Any]) -> str | None:
    sources = _context_sources(event)

    explicit_status = _first_status_name(sources, EXPLICIT_STATUS_KEYS)
    if explicit_status:
        return explicit_status

    changed_status = _status_from_changes(sources)
    if changed_status:
        return changed_status

    return _first_status_name(sources, CURRENT_STATUS_KEYS)


def _context_sources(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    sources: list[Mapping[str, Any]] = []

    def append(value: Any) -> None:
        if isinstance(value, Mapping) and value not in sources:
            sources.append(value)

    append(event.get("triggerContext"))
    append(event.get("data"))
    data = event.get("data")
    if isinstance(data, Mapping):
        append(data.get("issue"))
        append(data.get("node"))
    append(event.get("issue"))
    append(event)
    return sources


def _issue_sources(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    sources: list[Mapping[str, Any]] = []

    def append(value: Any) -> None:
        if isinstance(value, Mapping) and value not in sources:
            sources.append(value)

    append(event.get("triggerContext"))
    data = event.get("data")
    if isinstance(data, Mapping):
        append(data.get("issue"))
        append(data.get("node"))
    append(event.get("issue"))
    append(data)
    append(event)
    return sources


def _event_name_values(event: Mapping[str, Any]) -> Iterable[Any]:
    keys = ("trigger", "webhookType", "action", "type", "eventType")
    for source in _context_sources(event):
        for key in keys:
            value = source.get(key)
            if value is not None:
                yield value


def _status_field_changed(event: Mapping[str, Any]) -> bool:
    for source in _context_sources(event):
        for key in ("updatedFields", "changedFields"):
            if _contains_status_field(source.get(key)):
                return True

        changes = source.get("changes")
        if isinstance(changes, Mapping):
            if any(_normalize(field) in STATUS_FIELDS for field in changes):
                return True
        elif isinstance(changes, list):
            for change in changes:
                if isinstance(change, Mapping) and _change_field_is_status(change):
                    return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize(value) in STATUS_FIELDS

    if isinstance(value, Iterable) and not isinstance(value, (str, bytes, Mapping)):
        return any(_contains_status_field(item) for item in value)

    return False


def _status_from_changes(sources: Iterable[Mapping[str, Any]]) -> str | None:
    for source in sources:
        changes = source.get("changes")
        if isinstance(changes, Mapping):
            for field, change in changes.items():
                if _normalize(field) not in STATUS_FIELDS:
                    continue
                status = _changed_status_name(change)
                if status:
                    return status
        elif isinstance(changes, list):
            for change in changes:
                if not isinstance(change, Mapping) or not _change_field_is_status(change):
                    continue
                status = _changed_status_name(change)
                if status:
                    return status

    return None


def _change_field_is_status(change: Mapping[str, Any]) -> bool:
    field = _first_raw(change, ("field", "fieldName", "name", "key", "property"))
    return _normalize(field) in STATUS_FIELDS


def _changed_status_name(change: Any) -> str | None:
    if isinstance(change, Mapping):
        for key in ("newValue", "new_value", "new", "to", "after", "current", "value"):
            status = _status_name(change.get(key))
            if status:
                return status

    return _status_name(change)


def _first_status_name(sources: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for source in sources:
        for key in keys:
            status = _status_name(source.get(key))
            if status:
                return status
    return None


def _status_name(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "status", "state", "workflowState"):
            status = _status_name(value.get(key))
            if status:
                return status

    return None


def _first_text(sources: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for source in sources:
        value = _first_raw(source, keys)
        if isinstance(value, str):
            stripped = value.strip()
            if stripped:
                return stripped
    return None


def _first_raw(source: Mapping[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        if key in source:
            return source[key]
    return None


def _normalize(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value.strip())
    return re.sub(r"[^a-z0-9]+", "", spaced.lower())


def _has_research_prefix(title: str) -> bool:
    return re.match(rf"^\s*{re.escape(PREFIX)}\b", title, flags=re.IGNORECASE) is not None


def main() -> None:
    event = json.load(sys.stdin)
    result = build_issue_title_update(event)
    json.dump(result, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
