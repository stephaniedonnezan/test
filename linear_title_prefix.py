"""Build Linear issue title updates for research-status transitions.

The module is intentionally transport-agnostic: webhook glue can pass a parsed
event payload to ``build_issue_title_update`` and apply the returned action with
the Linear API.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
TITLE_SEPARATOR = ": "

_STATUS_FIELD_NAMES = {"status", "state", "workflow state", "workflowstate"}
_DIRECT_STATUS_EVENTS = {
    "status changed",
    "status change",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
}
_GENERIC_UPDATE_EVENTS = {
    "issue updated",
    "updated issue",
    "issue update",
    "update",
    "updated",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title-update action for a transition to "to research".

    The return value is deliberately small and serializable so callers can wire
    it to their Linear client of choice:

    ``{"action": "update_issue_title", "issueId": "...", "title": "..."}``
    """

    if not isinstance(event, Mapping):
        return None

    candidates = _candidate_payloads(event)
    if not _is_status_change_event(candidates):
        return None

    status = _extract_new_status(candidates)
    if _normalize(status) != TARGET_STATUS:
        return None

    issue_id = _first_text(candidates, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_text(candidates, ("title", "issueTitle", "issue_title"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if title.casefold().startswith(PREFIX.casefold()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}{TITLE_SEPARATOR}{title}",
    }


def _candidate_payloads(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return likely event/issue payloads in issue-specific priority order."""

    candidates: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in candidates:
            candidates.append(value)

    def nested(mapping: Mapping[str, Any], *path: str) -> Any:
        value: Any = mapping
        for key in path:
            if not isinstance(value, Mapping):
                return None
            value = value.get(key)
        return value

    add(nested(event, "triggerContext"))
    add(nested(event, "payload", "triggerContext"))
    add(nested(event, "data", "issue"))
    add(nested(event, "payload", "data", "issue"))
    add(nested(event, "issue"))
    add(nested(event, "payload", "issue"))
    add(nested(event, "data"))
    add(nested(event, "payload", "data"))
    add(nested(event, "payload"))
    add(event)

    return candidates


def _is_status_change_event(candidates: Iterable[Mapping[str, Any]]) -> bool:
    event_values = _event_type_values(candidates)
    if any(value in _DIRECT_STATUS_EVENTS for value in event_values):
        return True

    if any(value in _GENERIC_UPDATE_EVENTS for value in event_values):
        return _updated_fields_include_status(candidates)

    return False


def _event_type_values(candidates: Iterable[Mapping[str, Any]]) -> set[str]:
    keys = ("trigger", "webhookType", "webhook_type", "action", "type", "eventType", "event_type")
    values: set[str] = set()
    for candidate in candidates:
        for key in keys:
            value = candidate.get(key)
            if isinstance(value, str):
                values.add(_normalize(value))
    return values


def _updated_fields_include_status(candidates: Iterable[Mapping[str, Any]]) -> bool:
    for candidate in candidates:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields", "changes", "updatedFrom"):
            names = _field_names(candidate.get(key))
            if any(_is_status_field(name) for name in names):
                return True
    return False


def _field_names(value: Any) -> set[str]:
    names: set[str] = set()

    if isinstance(value, str):
        names.add(value)
        for part in re.split(r"[,;\s]+", value):
            if part:
                names.add(part)
        return names

    if isinstance(value, Mapping):
        for key, nested_value in value.items():
            names.add(str(key))
            if key in {"field", "name", "key", "property", "path"} and isinstance(nested_value, str):
                names.add(nested_value)
            elif isinstance(nested_value, Mapping):
                names.update(_field_names(nested_value))
        return names

    if isinstance(value, Iterable):
        for item in value:
            names.update(_field_names(item))

    return names


def _is_status_field(name: str) -> bool:
    normalized = _normalize(name)
    return normalized in _STATUS_FIELD_NAMES or normalized.endswith(" status")


def _extract_new_status(candidates: Iterable[Mapping[str, Any]]) -> str | None:
    explicit_keys = (
        "newStatus",
        "new_status",
        "toStatus",
        "to_status",
        "newState",
        "new_state",
        "status",
        "state",
        "workflowState",
        "workflow_state",
    )

    for candidate in candidates:
        for key in explicit_keys:
            status = _status_text(candidate.get(key))
            if status:
                return status

    for candidate in candidates:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields", "changes"):
            status = _status_from_change_value(candidate.get(key))
            if status:
                return status

    return None


def _status_from_change_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key, nested_value in value.items():
            if _is_status_field(str(key)):
                status = _status_text(nested_value)
                if status:
                    return status
            status = _status_from_change_value(nested_value)
            if status:
                return status

    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        for item in value:
            status = _status_from_change_value(item)
            if status:
                return status

    return None


def _status_text(value: Any) -> str | None:
    if value is None:
        return None

    if isinstance(value, Mapping):
        for key in ("newValue", "new_value", "to", "after", "value", "name", "status", "title"):
            status = _status_text(value.get(key))
            if status:
                return status
        return None

    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None

    return str(value).strip() or None


def _first_text(candidates: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for candidate in candidates:
        for key in keys:
            value = candidate.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _normalize(value: str | None) -> str | None:
    if value is None:
        return None

    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", str(value).strip())
    spaced = re.sub(r"[_\-/]+", " ", spaced)
    spaced = re.sub(r"[^A-Za-z0-9]+", " ", spaced)
    return " ".join(spaced.casefold().split())


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
