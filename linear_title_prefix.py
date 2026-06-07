"""Build Linear issue title updates for issues entering research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_DIRECT_STATUS_CHANGE_EVENTS = {
    "status changed",
    "status change",
    "issue status changed",
    "workflow state changed",
    "state changed",
}

_UPDATE_EVENTS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}

_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflowstate",
    "workflow state",
    "workflow_state",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to To Research."""
    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    if _normalized_status(_find_status(event)) != TARGET_STATUS:
        return None

    issue_id = _find_issue_id(event)
    title = _find_title(event)
    if not issue_id or not title or _already_prefixed(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    for source in _metadata_sources(event):
        for key in ("trigger", "webhookType", "eventType", "type", "action"):
            normalized = _normalize_words(source.get(key))
            if not normalized:
                continue
            if normalized in _DIRECT_STATUS_CHANGE_EVENTS:
                return True
            if normalized in _UPDATE_EVENTS and _updated_fields_include_status(source):
                return True

        if _updated_fields_include_status(source):
            return True

    return False


def _find_status(event: Mapping[str, Any]) -> Any:
    status_keys = (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "statusName",
        "stateName",
        "workflowStateName",
        "status",
        "state",
        "workflowState",
        "workflow_state",
    )

    for source in _metadata_sources(event) + _issue_sources(event):
        for key in status_keys:
            value = source.get(key)
            if value is not None:
                return _named_value(value)

    return None


def _find_issue_id(event: Mapping[str, Any]) -> str | None:
    # Prefer human-readable Linear identifiers over internal UUID-style ids.
    for source in _issue_sources(event):
        for key in ("issueId", "issue_id", "identifier", "key", "id"):
            value = source.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _find_title(event: Mapping[str, Any]) -> str | None:
    for source in _issue_sources(event):
        for key in ("title", "issueTitle", "issue_title", "name"):
            value = source.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _metadata_sources(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    sources: list[Mapping[str, Any]] = []
    for value in (event, event.get("triggerContext"), event.get("data")):
        if isinstance(value, Mapping):
            sources.append(value)
    return sources


def _issue_sources(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    sources: list[Mapping[str, Any]] = []

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        sources.append(trigger_context)

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        sources.append(issue)

    data = event.get("data")
    if isinstance(data, Mapping):
        data_issue = data.get("issue")
        if isinstance(data_issue, Mapping):
            sources.append(data_issue)
        sources.append(data)

    sources.append(event)
    return sources


def _updated_fields_include_status(source: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        if _field_collection_includes_status(source.get(key)):
            return True

    changes = source.get("changes")
    if isinstance(changes, Mapping):
        return any(_is_status_field_name(field) for field in changes.keys())

    return _field_collection_includes_status(changes)


def _field_collection_includes_status(fields: Any) -> bool:
    if isinstance(fields, str):
        return _is_status_field_name(fields)

    if isinstance(fields, Mapping):
        names = list(fields.keys())
        for key in ("field", "fieldName", "name"):
            if key in fields:
                names.append(fields[key])
        return any(_is_status_field_name(name) for name in names)

    if isinstance(fields, Iterable):
        return any(_field_collection_includes_status(field) for field in fields)

    return False


def _is_status_field_name(value: Any) -> bool:
    normalized = _normalize_words(value)
    compact = normalized.replace(" ", "") if normalized else ""
    return normalized in _STATUS_FIELD_NAMES or compact in _STATUS_FIELD_NAMES


def _named_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            named = value.get(key)
            if named is not None:
                return named
    return value


def _normalized_status(value: Any) -> str | None:
    return _normalize_words(_named_value(value))


def _normalize_words(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    normalized = re.sub(r"[^A-Za-z0-9]+", " ", spaced).strip().lower()
    return re.sub(r"\s+", " ", normalized) if normalized else None


def _already_prefixed(title: str) -> bool:
    return title.strip().lower().startswith(PREFIX.lower())


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 1

    update = build_issue_title_update(event)
    if update is None:
        return 1

    print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
