"""Build title update actions for Linear issues entering research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflowstatus", "workflow state"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue title update action when a Linear issue moves to research."""
    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    new_status = _find_new_status(event)
    if _normalize_text(new_status) != TARGET_STATUS:
        return None

    issue_id = _find_issue_id(event)
    title = _find_title(event)
    if not issue_id or not title:
        return None

    title = title.strip()
    if not title or _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    metadata_values = []
    for context in _contexts(event):
        metadata_values.extend(
            str(context[key])
            for key in ("trigger", "webhookType", "action", "type", "event", "eventType")
            if isinstance(context.get(key), str)
        )

    normalized_metadata = {_normalize_text(value) for value in metadata_values}
    if normalized_metadata & {"status changed", "state changed", "workflow state changed"}:
        return True

    if any("status changed" in value or "state changed" in value for value in normalized_metadata):
        return True

    update_events = {"update", "updated", "issue updated", "updated issue"}
    if normalized_metadata & update_events:
        return _status_field_changed(event)

    return _status_field_changed(event) and _find_new_status(event) is not None


def _status_field_changed(event: Mapping[str, Any]) -> bool:
    for context in _contexts(event):
        updated_fields = context.get("updatedFields") or context.get("updated_fields")
        if _field_collection_contains_status(updated_fields):
            return True

        for key in ("changes", "changedFields", "changed_fields"):
            changes = context.get(key)
            if isinstance(changes, Mapping) and any(_is_status_field(field) for field in changes):
                return True
            if _field_collection_contains_status(changes):
                return True

    return False


def _find_new_status(event: Mapping[str, Any]) -> str | None:
    explicit_keys = (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "toStatus",
        "to_status",
        "statusName",
        "status_name",
        "stateName",
        "state_name",
    )
    for context in _contexts(event):
        value = _first_string(context, explicit_keys)
        if value:
            return value

    for context in _contexts(event):
        for change_key in ("changes", "changedFields", "changed_fields"):
            status = _status_from_changes(context.get(change_key))
            if status:
                return status

    fallback_keys = ("status", "workflowStatus")
    for context in _contexts(event):
        value = _first_string(context, fallback_keys)
        if value:
            return value

        for key in ("state", "workflowState", "workflow_state"):
            value = _string_from_status_value(context.get(key))
            if value:
                return value

    return None


def _find_issue_id(event: Mapping[str, Any]) -> str | None:
    for context in _issue_contexts(event):
        value = _first_string(context, ("issueId", "issue_id", "identifier", "key", "id"))
        if value:
            return value
    return None


def _find_title(event: Mapping[str, Any]) -> str | None:
    for context in _issue_contexts(event):
        value = _first_string(context, ("title", "issueTitle", "issue_title"))
        if value:
            return value
    return None


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []
    _append_mapping(contexts, event.get("triggerContext"))
    _append_mapping(contexts, event)
    _append_mapping(contexts, event.get("data"))
    _append_mapping(contexts, _mapping_at(event, "data", "issue"))
    _append_mapping(contexts, event.get("issue"))
    return contexts


def _issue_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []
    _append_mapping(contexts, event.get("triggerContext"))
    _append_mapping(contexts, _mapping_at(event, "triggerContext", "issue"))
    _append_mapping(contexts, _mapping_at(event, "data", "issue"))
    _append_mapping(contexts, event.get("issue"))
    _append_mapping(contexts, event.get("data"))
    _append_mapping(contexts, event)
    return contexts


def _append_mapping(contexts: list[Mapping[str, Any]], value: Any) -> None:
    if isinstance(value, Mapping) and value not in contexts:
        contexts.append(value)


def _mapping_at(mapping: Mapping[str, Any], *path: str) -> Mapping[str, Any] | None:
    current: Any = mapping
    for key in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current if isinstance(current, Mapping) else None


def _field_collection_contains_status(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(_is_status_field(field) for field in value)
    if isinstance(value, str):
        return _is_status_field(value)
    if isinstance(value, Iterable):
        return any(isinstance(field, str) and _is_status_field(field) for field in value)
    return False


def _is_status_field(value: str) -> bool:
    normalized = _normalize_text(value).replace(" ", "")
    return normalized in STATUS_FIELD_NAMES


def _status_from_changes(changes: Any) -> str | None:
    if not isinstance(changes, Mapping):
        return None

    for field, value in changes.items():
        if not _is_status_field(str(field)):
            continue
        if isinstance(value, Mapping):
            for key in ("to", "new", "after", "current", "name"):
                status = _string_from_status_value(value.get(key))
                if status:
                    return status
        status = _string_from_status_value(value)
        if status:
            return status

    return None


def _string_from_status_value(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        return _first_string(value, ("name", "title", "status", "state"))
    return None


def _first_string(mapping: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, Mapping):
            nested = _string_from_status_value(value)
            if nested:
                return nested.strip()
    return None


def _normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    spaced = re.sub(r"[^A-Za-z0-9]+", " ", spaced)
    return " ".join(spaced.casefold().split())


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())


def main() -> int:
    payload = json.load(sys.stdin)
    update = build_issue_title_update(payload)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
