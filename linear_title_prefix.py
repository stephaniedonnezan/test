"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"

_TRIGGER_KEYS = ("trigger", "webhookType", "action", "type", "triggerType")
_EXPLICIT_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "toStatus",
    "to_status",
    "toState",
    "to_state",
    "statusName",
    "stateName",
)
_STATUS_KEYS = ("status", "state", "workflowState")
_UPDATED_FIELD_KEYS = (
    "updatedFields",
    "updated_fields",
    "changedFields",
    "changed_fields",
)
_ISSUE_ID_KEYS = ("id", "issueId", "issue_id", "identifier")


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear issue-title update action for issues moved to research."""

    if not isinstance(event, Mapping):
        return None

    mappings = _collect_mappings(event)
    if not _is_status_change_event(mappings):
        return None

    if _normalize_status(_extract_status(mappings)) != RESEARCH_STATUS:
        return None

    title = _extract_title(mappings)
    issue_id = _extract_issue_id(mappings)
    if not title or not issue_id:
        return None

    stripped_title = title.strip()
    if _has_research_prefix(stripped_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {stripped_title}",
    }


def _collect_mappings(root: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    mappings: list[Mapping[str, Any]] = []
    queue: list[Mapping[str, Any]] = [root]
    seen: set[int] = set()

    while queue:
        current = queue.pop(0)
        current_id = id(current)
        if current_id in seen:
            continue
        seen.add(current_id)
        mappings.append(current)

        for key in ("triggerContext", "data", "payload", "issue"):
            value = current.get(key)
            if isinstance(value, Mapping):
                queue.append(value)

    return mappings


def _is_status_change_event(mappings: list[Mapping[str, Any]]) -> bool:
    trigger_values = [
        value
        for mapping in mappings
        for key in _TRIGGER_KEYS
        if isinstance((value := mapping.get(key)), str)
    ]

    saw_issue_update = False
    for value in trigger_values:
        normalized = _normalize_status(value)
        if normalized in {
            "status changed",
            "status change",
            "status updated",
            "status update",
            "statuschanged",
        }:
            return True

        if normalized in {"issue updated", "updated issue", "update", "updated"}:
            saw_issue_update = True

    return saw_issue_update and _has_status_updated_field(mappings)


def _has_status_updated_field(mappings: list[Mapping[str, Any]]) -> bool:
    for mapping in mappings:
        for key in _UPDATED_FIELD_KEYS:
            if _contains_status_field(mapping.get(key)):
                return True

        changes = mapping.get("changes")
        if isinstance(changes, Mapping) and any(
            _normalize_status(str(key)) in {"status", "state", "workflow state"}
            for key in changes.keys()
        ):
            return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_status(value) in {"status", "state", "workflow state"}

    if isinstance(value, Mapping):
        return any(_contains_status_field(key) for key in value.keys())

    if isinstance(value, Iterable):
        return any(_contains_status_field(item) for item in value)

    return False


def _extract_status(mappings: list[Mapping[str, Any]]) -> str | None:
    for mapping in mappings:
        value = _first_string(mapping, _EXPLICIT_STATUS_KEYS)
        if value:
            return value

    for mapping in mappings:
        for key in _STATUS_KEYS:
            value = mapping.get(key)
            if isinstance(value, str):
                return value
            if isinstance(value, Mapping):
                name = value.get("name")
                if isinstance(name, str):
                    return name

    return None


def _extract_title(mappings: list[Mapping[str, Any]]) -> str | None:
    return _first_string(mappings, ("title",))


def _extract_issue_id(mappings: list[Mapping[str, Any]]) -> str | None:
    return _first_string(mappings, _ISSUE_ID_KEYS)


def _first_string(
    mappings: Mapping[str, Any] | Iterable[Mapping[str, Any]], keys: Iterable[str]
) -> str | None:
    if isinstance(mappings, Mapping):
        mappings = (mappings,)

    for mapping in mappings:
        for key in keys:
            value = mapping.get(key)
            if isinstance(value, str) and value.strip():
                return value

    return None


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(TITLE_PREFIX.casefold())


def _normalize_status(value: str | None) -> str:
    if not value:
        return ""

    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    spaced = re.sub(r"[_\-]+", " ", spaced)
    spaced = re.sub(r"[^A-Za-z0-9]+", " ", spaced)
    return " ".join(spaced.casefold().split())


def main() -> int:
    event = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(event)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
