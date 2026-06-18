"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
UPDATE_ACTION = "update_issue_title"
TARGET_STATUS_KEY = "toresearch"
STATUS_FIELD_KEYS = {
    "status",
    "statusid",
    "state",
    "stateid",
    "workflowstate",
    "workflowstateid",
}
NEW_STATUS_KEYS = {
    "newstatus",
    "tostatus",
    "statusname",
    "newstate",
    "newstatename",
    "tostate",
    "workflowstatename",
    "newworkflowstate",
    "newworkflowstatename",
}
NEW_VALUE_KEYS = {"new", "newvalue", "to", "after", "current", "value"}
ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "key", "id")


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to to research."""

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    new_status = _extract_new_status(event)
    if _normalize_key(new_status) != TARGET_STATUS_KEY:
        return None

    issue_id = _first_non_blank(event, ISSUE_ID_KEYS)
    title = _first_non_blank(event, ("title",))
    if not issue_id or not title:
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id,
        "title": _prefixed_title(title),
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    for item in _iter_mappings(event):
        for key in ("trigger", "webhookType", "action", "type"):
            normalized = _normalize_words(item.get(key))
            if not normalized:
                continue
            words = set(normalized.split())
            if words & {"status", "state", "workflowstate"} and words & {
                "change",
                "changed",
                "update",
                "updated",
            }:
                return True

    return _has_status_change_metadata(event)


def _has_status_change_metadata(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized_key = _normalize_key(key)
            if normalized_key in {"updatedfields", "changes", "updatedfrom"}:
                return _contains_status_field(item)
            if isinstance(item, (Mapping, list, tuple)):
                if _has_status_change_metadata(item):
                    return True
    elif isinstance(value, (list, tuple)):
        return any(_has_status_change_metadata(item) for item in value)
    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized_key = _normalize_key(key)
            if normalized_key in STATUS_FIELD_KEYS:
                return True
            if normalized_key in {"field", "fieldname", "name", "key"}:
                if _normalize_key(item) in STATUS_FIELD_KEYS:
                    return True
            if _contains_status_field(item):
                return True
    elif isinstance(value, str):
        return _normalize_key(value) in STATUS_FIELD_KEYS
    elif isinstance(value, Iterable):
        return any(_contains_status_field(item) for item in value)
    return False


def _extract_new_status(event: Mapping[str, Any]) -> str | None:
    for item in _iter_mappings(event):
        for key, value in item.items():
            if _normalize_key(key) in NEW_STATUS_KEYS:
                status = _status_name(value)
                if status:
                    return status

    status_from_changes = _new_status_from_change_metadata(event)
    if status_from_changes:
        return status_from_changes

    for item in _issue_contexts(event):
        for key in ("status", "state", "workflowState", "workflow_state"):
            status = _status_name(item.get(key))
            if status:
                return status

    return None


def _new_status_from_change_metadata(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized_key = _normalize_key(key)
            if normalized_key in {"changes", "updatedfields"}:
                status = _new_status_from_changes_container(item)
                if status:
                    return status
            if isinstance(item, (Mapping, list, tuple)):
                status = _new_status_from_change_metadata(item)
                if status:
                    return status
    elif isinstance(value, (list, tuple)):
        for item in value:
            status = _new_status_from_change_metadata(item)
            if status:
                return status
    return None


def _new_status_from_changes_container(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if _normalize_key(key) in STATUS_FIELD_KEYS:
                return _new_status_from_change_value(item)
            if isinstance(item, Mapping):
                field_name = item.get("field") or item.get("fieldName") or item.get("name")
                if _normalize_key(field_name) in STATUS_FIELD_KEYS:
                    return _new_status_from_change_value(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            if isinstance(item, str) and _normalize_key(item) in STATUS_FIELD_KEYS:
                return None
            if isinstance(item, Mapping):
                field_name = item.get("field") or item.get("fieldName") or item.get("name")
                if _normalize_key(field_name) in STATUS_FIELD_KEYS:
                    status = _new_status_from_change_value(item)
                    if status:
                        return status
    return None


def _new_status_from_change_value(value: Any) -> str | None:
    if isinstance(value, str):
        return value

    if not isinstance(value, Mapping):
        return None

    for key in ("newValue", "new", "to", "after", "current", "value"):
        if _normalize_key(key) in NEW_VALUE_KEYS:
            status = _status_name(value.get(key))
            if status:
                return status

    return _status_name(value)


def _status_name(value: Any) -> str | None:
    if isinstance(value, str):
        trimmed = value.strip()
        return trimmed or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            status = _status_name(value.get(key))
            if status:
                return status

    return None


def _first_non_blank(event: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for item in _issue_contexts(event):
        for key in keys:
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _issue_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        contexts.append(trigger_context)

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            contexts.append(issue)
        contexts.append(data)

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        contexts.append(issue)

    contexts.append(event)
    return contexts


def _iter_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for item in value.values():
            yield from _iter_mappings(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _iter_mappings(item)


def _prefixed_title(title: str) -> str:
    trimmed = title.strip()
    if trimmed.lower().startswith(PREFIX.lower()):
        return trimmed
    return f"{PREFIX}: {trimmed}"


def _normalize_words(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    words = re.sub(r"[^A-Za-z0-9]+", " ", separated).lower().split()
    return " ".join(words)


def _normalize_key(value: Any) -> str:
    return _normalize_words(value).replace(" ", "")


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
