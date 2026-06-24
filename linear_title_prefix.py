"""Build Linear issue title updates for Cursor research status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow state", "stateid", "statusid"}
DIRECT_STATUS_CHANGE_EVENTS = {
    "status changed",
    "state changed",
    "workflow state changed",
    "status change",
    "state change",
    "workflow state change",
}
ISSUE_UPDATE_EVENTS = {"update", "updated", "issue update", "issue updated", "updated issue"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to To Research.

    The handler accepts the flat Cursor automation trigger context shape as well
    as nested Linear webhook payloads. It returns a side-effect-free action that
    a caller can use to update the issue title.
    """

    if not isinstance(event, Mapping):
        return None

    sources = _event_sources(event)
    if not _is_status_change_event(sources):
        return None

    new_status = _first_status_value(sources)
    if not _is_target_status(new_status):
        return None

    issue_id = _first_string(sources, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_string(sources, ("title",))
    if issue_id is None or title is None:
        return None

    stripped_title = title.strip()
    if not stripped_title or _has_research_prefix(stripped_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {stripped_title}",
    }


def _event_sources(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    sources: list[Mapping[str, Any]] = []

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        sources.append(trigger_context)

    sources.append(event)

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        sources.append(issue)

    data = event.get("data")
    if isinstance(data, Mapping):
        data_issue = data.get("issue")
        if isinstance(data_issue, Mapping):
            sources.append(data_issue)
        sources.append(data)

    return sources


def _is_status_change_event(sources: Iterable[Mapping[str, Any]]) -> bool:
    source_list = list(sources)
    event_names = _event_names(source_list)
    if any(event_name in DIRECT_STATUS_CHANGE_EVENTS for event_name in event_names):
        return True

    if any(event_name in ISSUE_UPDATE_EVENTS for event_name in event_names):
        return any(_has_status_change_marker(source) for source in source_list)

    return False


def _event_names(sources: Iterable[Mapping[str, Any]]) -> set[str]:
    names: set[str] = set()
    for source in sources:
        for key in ("trigger", "action", "event", "eventType", "type"):
            value = source.get(key)
            if isinstance(value, str):
                names.add(_normalize_text(value))
    return names


def _has_status_change_marker(source: Mapping[str, Any]) -> bool:
    if any(key in source for key in ("newStatus", "new_status", "previousStatus", "oldStatus")):
        return True

    for key in ("updatedFields", "changedFields"):
        if _contains_status_field(source.get(key)):
            return True

    for key in ("changes", "changed", "updatedFrom", "previousValues"):
        value = source.get(key)
        if isinstance(value, Mapping) and _contains_status_field(value.keys()):
            return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_text(value) in STATUS_FIELDS

    if isinstance(value, Mapping):
        value = value.keys()

    if isinstance(value, Iterable):
        return any(isinstance(item, str) and _normalize_text(item) in STATUS_FIELDS for item in value)

    return False


def _first_status_value(sources: Iterable[Mapping[str, Any]]) -> str | None:
    for key in ("newStatus", "new_status", "statusName", "stateName", "workflowStateName"):
        value = _first_string(sources, (key,))
        if value is not None:
            return value

    for source in sources:
        for key in ("status", "state", "workflowState"):
            value = source.get(key)
            if isinstance(value, str) and value.strip():
                return value
            if isinstance(value, Mapping):
                name = value.get("name")
                if isinstance(name, str) and name.strip():
                    return name

    return None


def _first_string(sources: Iterable[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for source in sources:
        for key in keys:
            value = source.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _is_target_status(value: str | None) -> bool:
    return value is not None and _normalize_text(value) == TARGET_STATUS


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def _normalize_text(value: str) -> str:
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    normalized = re.sub(r"[^A-Za-z0-9]+", " ", spaced)
    return " ".join(normalized.lower().split())


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON payload: {exc}", file=sys.stderr)
        return 2

    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, indent=2, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
