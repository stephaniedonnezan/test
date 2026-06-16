"""Build Linear issue title updates for issues moved to research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
ACTION = "update_issue_title"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "stateid",
    "workflowstate",
    "workflowstateid",
}
_DIRECT_STATUS_CHANGE_EVENTS = {
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
    "issue update",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to To Research."""

    if not isinstance(event, Mapping):
        return None

    sources = _candidate_sources(event)
    if not _is_status_change_event(event, sources):
        return None

    new_status = _extract_new_status(sources)
    if _normalize_text(new_status) != TARGET_STATUS:
        return None

    issue_id = _first_string(sources, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_string(sources, ("title",))
    if issue_id is None or title is None:
        return None

    issue_id = issue_id.strip()
    title = title.strip()
    if not issue_id or not title or _already_prefixed(title):
        return None

    return {
        "action": ACTION,
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _candidate_sources(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return likely issue/trigger dictionaries from most to least specific."""

    sources: list[Mapping[str, Any]] = []
    trigger_context = _mapping_at(event, ("triggerContext",))
    data = _mapping_at(event, ("data",))

    for source in (
        trigger_context,
        _mapping_at(trigger_context, ("issue",)),
        _mapping_at(trigger_context, ("data", "issue")),
        _mapping_at(event, ("issue",)),
        _mapping_at(data, ("issue",)),
        data,
        event,
    ):
        if source is not None and not any(source is existing for existing in sources):
            sources.append(source)

    return sources


def _is_status_change_event(
    event: Mapping[str, Any], sources: Iterable[Mapping[str, Any]]
) -> bool:
    event_names = {
        _normalize_text(value)
        for source in sources
        for key in ("trigger", "action", "type", "event", "eventType", "webhookType")
        if isinstance((value := source.get(key)), str)
    }

    if event_names & _DIRECT_STATUS_CHANGE_EVENTS:
        return True

    if event_names & _GENERIC_UPDATE_EVENTS:
        return _has_status_update_marker(event)

    return False


def _has_status_update_marker(value: Any) -> bool:
    if not isinstance(value, Mapping):
        return False

    for key, item in value.items():
        normalized_key = _normalize_field_name(str(key))
        if normalized_key in {"updatedfields", "changedfields"}:
            if _contains_status_field(item):
                return True
        elif normalized_key in {"changes", "updatedfrom", "previousvalues"}:
            if _mapping_mentions_status(item):
                return True
        elif isinstance(item, Mapping) and _has_status_update_marker(item):
            return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_field_name(value) in _STATUS_FIELD_NAMES

    if isinstance(value, Mapping):
        return any(_normalize_field_name(str(key)) in _STATUS_FIELD_NAMES for key in value)

    if isinstance(value, Iterable):
        return any(_contains_status_field(item) for item in value)

    return False


def _mapping_mentions_status(value: Any) -> bool:
    if not isinstance(value, Mapping):
        return False

    for key, item in value.items():
        if _normalize_field_name(str(key)) in _STATUS_FIELD_NAMES:
            return True
        if isinstance(item, Mapping) and _mapping_mentions_status(item):
            return True

    return False


def _extract_new_status(sources: Iterable[Mapping[str, Any]]) -> str | None:
    direct_keys = (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "statusName",
        "status_name",
        "stateName",
        "state_name",
        "workflowStateName",
        "workflow_state_name",
    )
    direct = _first_string(sources, direct_keys)
    if direct is not None:
        return direct

    for source in sources:
        changed_status = _status_from_changes(source.get("changes"))
        if changed_status is not None:
            return changed_status

    for source in sources:
        for key in ("status", "state", "workflowState", "workflow_state"):
            value = source.get(key)
            status = _string_or_named_value(value)
            if status is not None:
                return status

    return None


def _status_from_changes(changes: Any) -> str | None:
    if not isinstance(changes, Mapping):
        return None

    for key in ("status", "state", "workflowState", "workflow_state"):
        if key not in changes:
            continue

        value = changes[key]
        if isinstance(value, Mapping):
            status = _first_string(
                (value,),
                ("newValue", "new_value", "after", "to", "name", "newName", "new_name"),
            )
            if status is not None:
                return status
        else:
            status = _string_or_named_value(value)
            if status is not None:
                return status

    return None


def _first_string(
    sources: Iterable[Mapping[str, Any]], keys: Iterable[str]
) -> str | None:
    for source in sources:
        for key in keys:
            value = source.get(key)
            if isinstance(value, str):
                return value
    return None


def _string_or_named_value(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        return _first_string((value,), ("name", "title"))
    return None


def _mapping_at(value: Any, path: Iterable[str]) -> Mapping[str, Any] | None:
    current = value
    for key in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current if isinstance(current, Mapping) else None


def _already_prefixed(title: str) -> bool:
    return re.match(rf"^\s*{re.escape(PREFIX)}\b", title, re.IGNORECASE) is not None


def _normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    spaced = re.sub(r"[_\-/]+", " ", spaced)
    return re.sub(r"\s+", " ", spaced).strip().lower()


def _normalize_field_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", _normalize_text(value))


def main() -> int:
    event = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(event), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
