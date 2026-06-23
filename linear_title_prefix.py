"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_MARKER = "Cursor researching"
TARGET_STATUS = "to research"

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
_STATUS_FIELD_TOKENS = {
    "status",
    "status id",
    "state",
    "state id",
    "workflow state",
    "workflow state id",
    "workflowstate",
    "workflowstate id",
}
_TRIGGER_KEYS = ("trigger", "event", "action", "type", "webhookType", "webhook_type")
_UPDATED_FIELD_KEYS = (
    "updatedFields",
    "updated_fields",
    "changedFields",
    "changed_fields",
    "updatedFrom",
    "updated_from",
    "changes",
    "changed",
)
_NEW_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "newWorkflowState",
    "new_workflow_state",
)
_STATUS_KEYS = (
    "status",
    "state",
    "workflowState",
    "workflow_state",
)
_ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "key", "id")
_TITLE_KEYS = ("title",)


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to to research."""
    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    status = _extract_new_status(event)
    if _normalize(status) != TARGET_STATUS:
        return None

    issue_id = _first_issue_text(event, _ISSUE_ID_KEYS)
    title = _first_issue_text(event, _TITLE_KEYS)
    if not issue_id or not title:
        return None

    stripped_title = title.strip()
    if _has_marker(stripped_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_MARKER}: {stripped_title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    trigger_values = [_normalize(value) for value in _recursive_key_values(event, _TRIGGER_KEYS)]

    if any(_is_direct_status_change(value) for value in trigger_values):
        return True

    is_update = any(value in _GENERIC_UPDATE_EVENTS for value in trigger_values)
    return is_update and _updated_fields_include_status(event)


def _is_direct_status_change(value: str) -> bool:
    if value in _DIRECT_STATUS_CHANGE_EVENTS:
        return True
    return ("status" in value or "state" in value) and "chang" in value


def _updated_fields_include_status(event: Mapping[str, Any]) -> bool:
    for value in _recursive_key_values(event, _UPDATED_FIELD_KEYS):
        for field_name in _field_names(value):
            if _normalize(field_name) in _STATUS_FIELD_TOKENS:
                return True
    return False


def _extract_new_status(event: Mapping[str, Any]) -> str:
    sources = _event_sources(event)

    for key in _NEW_STATUS_KEYS:
        for source in sources:
            value = _value_at(source, key)
            if value is not None:
                return _text(value)

    for key in _STATUS_KEYS:
        for source in sources:
            value = _value_at(source, key)
            if value is not None:
                return _text(value)

    return ""


def _first_issue_text(event: Mapping[str, Any], keys: Iterable[str]) -> str:
    sources = _issue_sources(event)
    for key in keys:
        for source in sources:
            value = _value_at(source, key)
            text = _text(value).strip()
            if text:
                return text
    return ""


def _event_sources(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    sources: list[Mapping[str, Any]] = [event]

    for key in ("triggerContext", "trigger_context", "data", "issue"):
        nested = event.get(key)
        if isinstance(nested, Mapping):
            sources.append(nested)

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            sources.append(issue)

    trigger_context = event.get("triggerContext") or event.get("trigger_context")
    if isinstance(trigger_context, Mapping):
        for key in ("data", "issue"):
            nested = trigger_context.get(key)
            if isinstance(nested, Mapping):
                sources.append(nested)

    return sources


def _issue_sources(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    sources: list[Mapping[str, Any]] = []

    for key in ("triggerContext", "trigger_context"):
        nested = event.get(key)
        if isinstance(nested, Mapping):
            sources.append(nested)

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            sources.append(issue)
        sources.append(data)

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        sources.append(issue)

    sources.append(event)
    return sources


def _recursive_key_values(value: Any, keys: Iterable[str]) -> Iterable[Any]:
    key_set = set(keys)
    if isinstance(value, Mapping):
        for key, item in value.items():
            if key in key_set:
                yield item
            yield from _recursive_key_values(item, key_set)
    elif isinstance(value, list):
        for item in value:
            yield from _recursive_key_values(item, key_set)


def _field_names(value: Any) -> Iterable[Any]:
    if isinstance(value, Mapping):
        yield from value.keys()
        for nested_key in ("field", "name"):
            nested_value = value.get(nested_key)
            if nested_value is not None:
                yield nested_value
    elif isinstance(value, str):
        yield value
    elif isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray)):
        for item in value:
            yield from _field_names(item)


def _value_at(source: Mapping[str, Any], key: str) -> Any:
    if key in source:
        return source[key]

    normalized_key = _normalize(key)
    for source_key, value in source.items():
        if _normalize(source_key) == normalized_key:
            return value
    return None


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            nested = value.get(key)
            if nested is not None:
                return _text(nested)
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def _normalize(value: Any) -> str:
    text = _text(value)
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def _has_marker(title: str) -> bool:
    return title.lower().startswith(TITLE_MARKER.lower())


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    result = build_issue_title_update(payload)
    if result is not None:
        print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
