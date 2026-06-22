"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow state"}
STATUS_CHANGE_TRIGGERS = {
    "status changed",
    "status change",
    "state changed",
    "workflow state changed",
}
ISSUE_UPDATE_TRIGGERS = {
    "issue updated",
    "updated issue",
    "update",
    "updated",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to research."""
    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_change(event, contexts):
        return None

    status = _new_status(contexts)
    if _normalize_value(status) != TARGET_STATUS:
        return None

    issue_id = _first_text(contexts, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_text(contexts, ("title", "name"))
    if issue_id is None or title is None:
        return None

    stripped_title = title.strip()
    if _has_prefix(stripped_title):
        new_title = stripped_title
    else:
        new_title = f"{PREFIX}: {stripped_title}"

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": new_title,
    }


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return likely payload locations, ordered from most explicit to fallback."""
    contexts: list[Mapping[str, Any]] = [event]
    for path in (
        ("triggerContext",),
        ("data",),
        ("issue",),
        ("data", "issue"),
        ("triggerContext", "issue"),
        ("triggerContext", "data"),
        ("triggerContext", "data", "issue"),
    ):
        value: Any = event
        for key in path:
            if not isinstance(value, Mapping):
                value = None
                break
            value = value.get(key)
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)
    return contexts


def _is_status_change(event: Mapping[str, Any], contexts: Sequence[Mapping[str, Any]]) -> bool:
    trigger_values = _all_text(contexts, ("trigger", "webhookType", "action", "type", "event"))
    normalized_triggers = {_normalize_value(value) for value in trigger_values}
    if normalized_triggers & STATUS_CHANGE_TRIGGERS:
        return True

    if not (normalized_triggers & ISSUE_UPDATE_TRIGGERS):
        return False

    return _updated_fields_include_status(event)


def _updated_fields_include_status(event: Mapping[str, Any]) -> bool:
    for value in _walk_values(event, {"updatedFields", "updated_fields"}):
        if _field_collection_contains_status(value):
            return True
    for value in _walk_values(event, {"changes", "changedFields", "changed_fields"}):
        if _changes_include_status(value):
            return True
    return False


def _field_collection_contains_status(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_field(value) in STATUS_FIELDS
    if isinstance(value, Mapping):
        return any(_field_collection_contains_status(key) for key in value)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return any(_field_collection_contains_status(item) for item in value)
    return False


def _changes_include_status(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(
            _normalize_field(str(key)) in STATUS_FIELDS or _changes_include_status(child)
            for key, child in value.items()
        )
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return any(_changes_include_status(item) for item in value)
    return _field_collection_contains_status(value)


def _new_status(contexts: Sequence[Mapping[str, Any]]) -> str | None:
    for keys in (
        ("newStatus", "new_status", "statusName", "status_name"),
        ("to", "newValue", "new_value"),
    ):
        status = _first_status_text(contexts, keys)
        if status is not None:
            return status

    for context in contexts:
        for key in ("state", "workflowState", "workflow_state", "status"):
            status = _status_text(context.get(key))
            if status is not None:
                return status
    return None


def _first_status_text(contexts: Sequence[Mapping[str, Any]], keys: Sequence[str]) -> str | None:
    for context in contexts:
        for key in keys:
            status = _status_text(context.get(key))
            if status is not None:
                return status
    return None


def _status_text(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value
    if isinstance(value, Mapping):
        return _first_text([value], ("name", "title", "status", "state"))
    return None


def _first_text(contexts: Sequence[Mapping[str, Any]], keys: Sequence[str]) -> str | None:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _all_text(contexts: Sequence[Mapping[str, Any]], keys: Sequence[str]) -> list[str]:
    values: list[str] = []
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                values.append(value)
    return values


def _walk_values(value: Any, keys: set[str]) -> list[Any]:
    matches: list[Any] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            if key in keys:
                matches.append(child)
            matches.extend(_walk_values(child, keys))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for child in value:
            matches.extend(_walk_values(child, keys))
    return matches


def _has_prefix(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())


def _normalize_value(value: str | None) -> str:
    if value is None:
        return ""
    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return re.sub(r"[\W_]+", " ", separated).strip().casefold()


def _normalize_field(value: str) -> str:
    return _normalize_value(value).replace(" ", "")


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
