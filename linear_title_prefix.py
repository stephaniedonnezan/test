"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"

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
_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflow state",
}
_EXPLICIT_NEW_STATUS_KEYS = {
    "new status",
    "new state",
    "new workflow state",
    "status name",
    "state name",
    "workflow state name",
}
_CURRENT_STATUS_KEYS = {
    "status",
    "state",
    "workflow state",
}
_ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "key", "id")
_TITLE_KEYS = ("title",)


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update action for Linear issues moved to "to research".

    The handler accepts the flattened Cursor automation payload shape and common
    nested Linear webhook shapes. It is intentionally side-effect free so the
    caller can decide how to execute the returned action.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    new_status = _extract_new_status(event)
    if _normalize(new_status) != TARGET_STATUS:
        return None

    issue_id = _extract_issue_id(event)
    title = _extract_title(event)
    if not issue_id or not title or _has_prefix(title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    event_names = {
        _normalize(value)
        for context in _contexts(event, issue_first=False)
        for key in ("trigger", "webhookType", "action", "type", "triggerType")
        if (value := context.get(key)) is not None
    }

    if event_names & _DIRECT_STATUS_CHANGE_EVENTS:
        return True

    if event_names & _GENERIC_UPDATE_EVENTS:
        return _changed_fields_include_status(event)

    return False


def _extract_new_status(event: Mapping[str, Any]) -> str | None:
    for status in _iter_changed_status_values(event):
        if status:
            return status

    for context in _contexts(event):
        for key, value in context.items():
            if _normalize(key) in _EXPLICIT_NEW_STATUS_KEYS:
                if status := _value_name(value):
                    return status

    for context in _contexts(event):
        for key, value in context.items():
            if _normalize(key) in _CURRENT_STATUS_KEYS:
                if status := _value_name(value):
                    return status

    return None


def _extract_issue_id(event: Mapping[str, Any]) -> str | None:
    for context in _contexts(event):
        for key in _ISSUE_ID_KEYS:
            if value := _clean_string(context.get(key)):
                return value
    return None


def _extract_title(event: Mapping[str, Any]) -> str | None:
    for context in _contexts(event):
        for key in _TITLE_KEYS:
            if value := _clean_string(context.get(key)):
                return value
    return None


def _contexts(event: Mapping[str, Any], issue_first: bool = True) -> list[Mapping[str, Any]]:
    """Return useful payload dictionaries, preferring issue data over metadata."""

    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)

    if issue_first:
        trigger_context = event.get("triggerContext")
        data = event.get("data")

        if isinstance(trigger_context, Mapping):
            add(trigger_context)
            add(trigger_context.get("issue"))
            add(trigger_context.get("data"))

        add(event.get("issue"))

        if isinstance(data, Mapping):
            add(data.get("issue"))
            add(data)

        add(event)
    else:
        add(event)
        add(event.get("triggerContext"))
        add(event.get("issue"))
        data = event.get("data")
        if isinstance(data, Mapping):
            add(data)
            add(data.get("issue"))

    return contexts


def _changed_fields_include_status(event: Mapping[str, Any]) -> bool:
    for field in _iter_changed_field_names(event):
        if _normalize(field) in _STATUS_FIELD_NAMES:
            return True
    return False


def _iter_changed_field_names(value: Any) -> Iterable[str]:
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized_key = _normalize(key)
            if normalized_key in {"updated fields", "changed fields"}:
                yield from _field_names_from_collection(child)
            elif normalized_key == "changes":
                yield from _field_names_from_changes(child)
            else:
                yield from _iter_changed_field_names(child)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_changed_field_names(item)


def _field_names_from_collection(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, Mapping):
        for key in ("field", "fieldName", "name", "key", "path"):
            if field := _clean_string(value.get(key)):
                yield field
    elif isinstance(value, list):
        for item in value:
            yield from _field_names_from_collection(item)


def _field_names_from_changes(value: Any) -> Iterable[str]:
    if isinstance(value, Mapping):
        for key, child in value.items():
            yield key
            if isinstance(child, Mapping):
                for field_key in ("field", "fieldName", "name", "key", "path"):
                    if field := _clean_string(child.get(field_key)):
                        yield field
    elif isinstance(value, list):
        for item in value:
            yield from _field_names_from_collection(item)


def _iter_changed_status_values(value: Any) -> Iterable[str | None]:
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized_key = _normalize(key)
            if normalized_key in {"changes", "updated fields", "changed fields"}:
                yield from _status_values_from_change_collection(child)
            else:
                yield from _iter_changed_status_values(child)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_changed_status_values(item)


def _status_values_from_change_collection(value: Any) -> Iterable[str | None]:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if _normalize(key) in _STATUS_FIELD_NAMES:
                yield _new_value_from_change(child)
            elif isinstance(child, Mapping):
                field = next(_field_names_from_collection(child), None)
                if field and _normalize(field) in _STATUS_FIELD_NAMES:
                    yield _new_value_from_change(child)
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, Mapping):
                field = next(_field_names_from_collection(item), None)
                if field and _normalize(field) in _STATUS_FIELD_NAMES:
                    yield _new_value_from_change(item)


def _new_value_from_change(value: Any) -> str | None:
    if not isinstance(value, Mapping):
        return _value_name(value)

    for key in (
        "to",
        "toValue",
        "newValue",
        "new_value",
        "after",
        "current",
        "value",
        "name",
    ):
        if status := _value_name(value.get(key)):
            return status
    return None


def _value_name(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("name", "displayName", "label", "title", "value", "id"):
            if result := _clean_string(value.get(key)):
                return result
        return None
    return _clean_string(value)


def _has_prefix(title: str) -> bool:
    return re.match(rf"^\s*{re.escape(TITLE_PREFIX)}\b", title, re.IGNORECASE) is not None


def _normalize(value: Any) -> str:
    text = _clean_string(value)
    if not text:
        return ""

    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def _clean_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    stripped = value.strip()
    return stripped or None


def main() -> int:
    event = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(event), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
