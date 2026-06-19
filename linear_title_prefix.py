"""Build Linear issue-title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_CAMEL_CASE_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")

_EVENT_KEYS = ("trigger", "webhookType", "webhook_type", "action", "type")
_NEW_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "toStatus",
    "to_status",
    "statusName",
    "status_name",
    "stateName",
    "state_name",
    "workflowStateName",
    "workflow_state_name",
)
_STATUS_KEYS = ("status", "state", "workflowState", "workflow_state")
_CHANGE_KEYS = ("changes", "updatedFields", "updated_fields", "updatedFrom", "updated_from")
_ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "key", "id")
_TITLE_KEYS = ("title",)


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear issue title update action for matching status-change events.

    The handler accepts both flat Cursor automation trigger contexts and nested
    Linear webhook payloads. It intentionally returns a serializable action
    instead of mutating Linear directly, so callers can decide how to perform the
    update.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _candidate_contexts(event)
    if not _is_status_change_event(contexts):
        return None

    if not _moved_to_target_status(contexts):
        return None

    issue_id = _first_string_value(_issue_sources(contexts), _ISSUE_ID_KEYS)
    title = _first_string_value(_issue_sources(contexts), _TITLE_KEYS)
    if not issue_id or not title:
        return None

    stripped_title = title.strip()
    if not stripped_title or stripped_title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {stripped_title}",
    }


def _candidate_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []
    seen: set[int] = set()

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and id(value) not in seen:
            contexts.append(value)
            seen.add(id(value))

    add(event)

    automation_info = event.get("automation_trigger_info") or event.get("automationTriggerInfo")
    if isinstance(automation_info, Mapping):
        add(automation_info.get("triggerContext"))
        add(automation_info.get("trigger_context"))

    add(event.get("triggerContext"))
    add(event.get("trigger_context"))

    index = 0
    while index < len(contexts):
        context = contexts[index]
        add(context.get("data"))
        add(context.get("issue"))
        add(context.get("triggerContext"))
        add(context.get("trigger_context"))

        data = context.get("data")
        if isinstance(data, Mapping):
            add(data.get("issue"))

        index += 1

    return contexts


def _issue_sources(contexts: Iterable[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    sources: list[Mapping[str, Any]] = []
    seen: set[int] = set()

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and id(value) not in seen:
            sources.append(value)
            seen.add(id(value))

    for context in contexts:
        add(context.get("issue"))
        data = context.get("data")
        if isinstance(data, Mapping):
            add(data.get("issue"))
        add(context)

    return sources


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    context_list = list(contexts)
    event_names = [_normalize_text(value) for value in _values_for_keys(context_list, _EVENT_KEYS)]

    if any(_is_direct_status_change(name) for name in event_names):
        return True

    return any(_is_generic_update(name) for name in event_names) and any(
        _has_status_change_marker(context) for context in context_list
    )


def _moved_to_target_status(contexts: Iterable[Mapping[str, Any]]) -> bool:
    return any(_normalize_text(status) == TARGET_STATUS for status in _status_candidates(contexts))


def _status_candidates(contexts: Iterable[Mapping[str, Any]]) -> Iterable[str]:
    context_list = list(contexts)

    for value in _values_for_keys(context_list, _NEW_STATUS_KEYS):
        status = _status_text(value)
        if status:
            yield status

    for context in context_list:
        for key in _CHANGE_KEYS:
            if key in context:
                yield from _status_values_from_change_payload(context[key])

    for value in _values_for_keys(context_list, _STATUS_KEYS):
        status = _status_text(value)
        if status:
            yield status


def _status_values_from_change_payload(payload: Any) -> Iterable[str]:
    if isinstance(payload, Mapping):
        for key, value in payload.items():
            if _is_status_field(key):
                status = _new_status_from_change(value)
                if status:
                    yield status
            elif isinstance(value, (Mapping, list, tuple)):
                yield from _status_values_from_change_payload(value)
        return

    if isinstance(payload, (list, tuple)):
        for item in payload:
            if isinstance(item, Mapping):
                field_name = _first_string_value((item,), ("field", "fieldName", "name", "key"))
                if field_name and _is_status_field(field_name):
                    status = _new_status_from_change(item)
                    if status:
                        yield status
            elif _is_status_field(item):
                yield from ()


def _new_status_from_change(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("to", "after", "new", "newValue", "new_value", "value", "current"):
            if key in value:
                status = _status_text(value[key])
                if status:
                    return status

        return _status_text(value)

    return _status_text(value)


def _has_status_change_marker(context: Mapping[str, Any]) -> bool:
    return any(
        _contains_status_change_marker(value)
        for key, value in context.items()
        if _normalize_key(key) in {_normalize_key(change_key) for change_key in _CHANGE_KEYS}
    )


def _contains_status_change_marker(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, nested_value in value.items():
            if _is_status_field(key):
                return True
            if _normalize_key(key) in {_normalize_key(change_key) for change_key in _CHANGE_KEYS}:
                if _contains_status_change_marker(nested_value):
                    return True
        return False

    if isinstance(value, (list, tuple)):
        return any(_contains_status_change_marker(item) for item in value)

    return _is_status_field(value)


def _values_for_keys(
    contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]
) -> Iterable[Any]:
    normalized_keys = {_normalize_key(key) for key in keys}
    for context in contexts:
        for key, value in context.items():
            if _normalize_key(key) in normalized_keys:
                yield value


def _first_string_value(
    contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]
) -> str | None:
    for value in _values_for_keys(contexts, keys):
        if isinstance(value, Mapping):
            value = _status_text(value)

        if value is None:
            continue

        text = str(value).strip()
        if text:
            return text

    return None


def _status_text(value: Any) -> str | None:
    if value is None:
        return None

    if isinstance(value, Mapping):
        for key in ("name", "title", "status", "state", "workflowState", "workflow_state"):
            if key in value:
                nested = _status_text(value[key])
                if nested:
                    return nested
        return None

    text = str(value).strip()
    return text or None


def _is_direct_status_change(event_name: str) -> bool:
    return event_name in {
        "status changed",
        "state changed",
        "workflow state changed",
    } or (("status" in event_name or "state" in event_name) and "changed" in event_name)


def _is_generic_update(event_name: str) -> bool:
    return event_name in {
        "update",
        "updated",
        "issue update",
        "issue updated",
        "updated issue",
    } or ("update" in event_name and "issue" in event_name)


def _is_status_field(value: Any) -> bool:
    key = _normalize_key(value)
    return key in {
        "status",
        "statusid",
        "state",
        "stateid",
        "workflowstate",
        "workflowstateid",
    }


def _normalize_key(value: Any) -> str:
    return _normalize_text(value).replace(" ", "")


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""

    text = str(value)
    text = _CAMEL_CASE_BOUNDARY.sub(" ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON: {exc}") from exc

    update = build_issue_title_update(event)
    if update:
        print(json.dumps(update, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
