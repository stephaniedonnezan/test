"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_EVENT_KEYS = ("trigger", "action", "type", "webhookType", "webhook_type", "event")
_DIRECT_STATUS_EVENTS = {
    "status changed",
    "status change",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
}
_UPDATE_EVENTS = {"update", "updated", "issue update", "issue updated", "updated issue"}
_NEW_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "toStatus",
    "to_status",
    "targetStatus",
    "target_status",
    "statusName",
    "status_name",
    "newState",
    "new_state",
    "toState",
    "to_state",
    "targetState",
    "target_state",
    "newWorkflowState",
    "new_workflow_state",
    "workflowStateName",
    "workflow_state_name",
)
_CURRENT_STATUS_KEYS = ("status", "state", "workflowState", "workflow_state")
_TITLE_KEYS = ("title", "name", "issueTitle", "issue_title")
_ISSUE_ID_KEYS = ("issueId", "issue_id", "id", "identifier", "key")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to To Research."""
    if not isinstance(event, Mapping):
        return None

    context = _mapping_value(event, "triggerContext")
    data = _mapping_value(event, "data")
    issue = _extract_issue(event, context, data)
    metadata_sources = tuple(source for source in (event, context, data) if source)

    if not _is_status_change_event(metadata_sources):
        return None

    new_status = _extract_new_status(metadata_sources, issue)
    if not _is_target_status(new_status):
        return None

    issue_id = _first_string(issue, _ISSUE_ID_KEYS) or _first_string(metadata_sources, _ISSUE_ID_KEYS)
    title = _first_string(issue, _TITLE_KEYS) or _first_string(metadata_sources, _TITLE_KEYS)
    if not issue_id or not title:
        return None

    stripped_title = title.strip()
    if not stripped_title or _has_prefix(stripped_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {stripped_title}",
    }


def _extract_issue(*sources: Mapping[str, Any]) -> Mapping[str, Any]:
    for source in sources:
        for key in ("issue", "Issue"):
            nested = _mapping_value(source, key)
            if nested:
                return nested

    for source in sources:
        data = _mapping_value(source, "data")
        nested = _mapping_value(data, "issue")
        if nested:
            return nested

    for source in sources:
        trigger_context = _mapping_value(source, "triggerContext")
        if trigger_context:
            return trigger_context

    return sources[0] if sources else {}


def _is_status_change_event(sources: tuple[Mapping[str, Any], ...]) -> bool:
    event_names = {_normalize(value) for source in sources for value in _values_for_keys(source, _EVENT_KEYS)}
    if event_names & _DIRECT_STATUS_EVENTS:
        return True

    has_update_event = bool(event_names & _UPDATE_EVENTS)
    has_status_change_details = _updated_fields_include_status(sources)
    return has_status_change_details and (has_update_event or not event_names)


def _updated_fields_include_status(sources: tuple[Mapping[str, Any], ...]) -> bool:
    for source in sources:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            fields = source.get(key)
            if _field_collection_mentions_status(fields):
                return True

        changes = source.get("changes") or source.get("changed") or source.get("change")
        if _changes_include_status(changes):
            return True

    return False


def _field_collection_mentions_status(fields: Any) -> bool:
    if isinstance(fields, str):
        return _is_status_field(fields)

    if isinstance(fields, Mapping):
        return any(_is_status_field(key) or _field_collection_mentions_status(value) for key, value in fields.items())

    if isinstance(fields, list | tuple | set):
        for field in fields:
            if isinstance(field, Mapping):
                names = (field.get(key) for key in ("field", "name", "key", "property", "path"))
                if any(_is_status_field(name) for name in names):
                    return True
            elif _is_status_field(field):
                return True

    return False


def _changes_include_status(changes: Any) -> bool:
    if isinstance(changes, Mapping):
        names = (changes.get(key) for key in ("field", "name", "key", "property", "path"))
        if any(_is_status_field(name) for name in names):
            return True

        return any(_is_status_field(key) or _changes_include_status(value) for key, value in changes.items())

    if isinstance(changes, list | tuple):
        return any(_changes_include_status(change) for change in changes)

    return False


def _extract_new_status(
    metadata_sources: tuple[Mapping[str, Any], ...],
    issue: Mapping[str, Any],
) -> str | None:
    for source in metadata_sources:
        for value in _values_for_keys(source, _NEW_STATUS_KEYS):
            status = _status_name(value)
            if status:
                return status

    for source in metadata_sources:
        status = _status_from_changes(source.get("changes") or source.get("changed") or source.get("change"))
        if status:
            return status

    for source in (issue, *metadata_sources):
        for value in _values_for_keys(source, _CURRENT_STATUS_KEYS):
            status = _status_name(value)
            if status:
                return status

    return None


def _status_from_changes(changes: Any) -> str | None:
    if isinstance(changes, Mapping):
        names = (changes.get(key) for key in ("field", "name", "key", "property", "path"))
        if any(_is_status_field(name) for name in names):
            status = _target_status_from_change(changes)
            if status:
                return status

        for key, value in changes.items():
            if _is_status_field(key):
                status = _target_status_from_change(value)
                if status:
                    return status

        for value in changes.values():
            status = _status_from_changes(value)
            if status:
                return status

    if isinstance(changes, list | tuple):
        for change in changes:
            status = _status_from_changes(change)
            if status:
                return status

    return None


def _target_status_from_change(change: Any) -> str | None:
    if isinstance(change, Mapping):
        for key in ("to", "after", "new", "newValue", "new_value", "current", "value", "name"):
            status = _status_name(change.get(key))
            if status:
                return status

    if isinstance(change, list | tuple) and change:
        return _status_name(change[-1])

    return _status_name(change)


def _mapping_value(source: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = source.get(key)
    return value if isinstance(value, Mapping) else {}


def _values_for_keys(source: Mapping[str, Any], keys: tuple[str, ...]) -> list[Any]:
    normalized_keys = {_normalize_key(key) for key in keys}
    return [value for key, value in source.items() if _normalize_key(key) in normalized_keys]


def _first_string(sources: Mapping[str, Any] | tuple[Mapping[str, Any], ...], keys: tuple[str, ...]) -> str | None:
    source_tuple = sources if isinstance(sources, tuple) else (sources,)
    for source in source_tuple:
        for value in _values_for_keys(source, keys):
            if isinstance(value, str) and value.strip():
                return value
    return None


def _status_name(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()

    if isinstance(value, Mapping):
        for key in ("name", "title", "status", "state", "workflowState", "workflow_state"):
            status = _status_name(value.get(key))
            if status:
                return status

    return None


def _normalize(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def _normalize_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", _normalize(value))


def _is_status_field(value: Any) -> bool:
    return _normalize_key(value) in {"status", "state", "workflowstate"}


def _is_target_status(value: Any) -> bool:
    return _normalize(value) == TARGET_STATUS


def _has_prefix(title: str) -> bool:
    return re.match(rf"^\s*{re.escape(PREFIX)}\b", title, re.IGNORECASE) is not None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    action = build_issue_title_update(payload)
    print(json.dumps(action, sort_keys=True) if action else "null")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
