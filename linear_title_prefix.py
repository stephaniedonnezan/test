"""Build Linear issue title updates for issues entering research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping, Sequence
from typing import Any


PREFIX = "Cursor researching"
UPDATE_ACTION = "update_issue_title"

_CAMEL_BOUNDARY = re.compile(r"([a-z0-9])([A-Z])")
_NON_WORD = re.compile(r"[^A-Za-z0-9]+")
_WHITESPACE = re.compile(r"\s+")

_TRIGGER_KEYS = ("trigger", "action", "type", "webhookType", "webhook_type", "eventType")
_UPDATE_FIELD_KEYS = ("updatedFields", "updated_fields", "changedFields", "changed_fields")
_STATUS_VALUE_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "toStatus",
    "to_status",
    "status",
    "state",
    "workflowState",
    "workflow_state",
    "statusName",
    "stateName",
    "workflowStateName",
)
_ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "key", "id")
_TITLE_KEYS = ("title", "name")
_STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflowstatus"}
_DIRECT_STATUS_CHANGE_TRIGGERS = {
    "statuschanged",
    "statuschange",
    "statusupdated",
    "statechanged",
    "statechange",
    "workflowstatechanged",
}
_ISSUE_UPDATE_TRIGGERS = {"update", "updated", "issueupdated", "updatedissue"}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title-update action when a Linear issue moves to research."""

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    if not any(_normalize_text(status) == "to research" for status in _status_candidates(event)):
        return None

    title = _first_text(event, _TITLE_KEYS)
    issue_id = _first_text(event, _ISSUE_ID_KEYS)
    if not title or not issue_id:
        return None

    if _has_research_prefix(title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def handle_issue_status_changed(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Compatibility wrapper for automation entrypoints."""

    return build_issue_title_update(event)


buildIssueTitleUpdate = build_issue_title_update
handleIssueStatusChanged = handle_issue_status_changed


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    trigger_values = {_compact(value) for value in _trigger_values(event)}
    if trigger_values & _DIRECT_STATUS_CHANGE_TRIGGERS:
        return True

    has_issue_update_trigger = bool(trigger_values & _ISSUE_UPDATE_TRIGGERS)
    has_status_fields = _has_updated_status_fields(event) or bool(list(_statuses_from_changes(event)))
    return has_issue_update_trigger and has_status_fields


def _trigger_values(event: Mapping[str, Any]) -> Iterable[str]:
    for context in _iter_mappings(event):
        for key in _TRIGGER_KEYS:
            value = context.get(key)
            if isinstance(value, str):
                yield value


def _has_updated_status_fields(event: Mapping[str, Any]) -> bool:
    for context in _iter_mappings(event):
        for key in _UPDATE_FIELD_KEYS:
            value = context.get(key)
            if any(_is_status_field(field) for field in _field_names(value)):
                return True
    return False


def _field_names(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, Mapping):
        for key in ("field", "name", "key", "type"):
            nested_value = value.get(key)
            if isinstance(nested_value, str):
                yield nested_value
        for nested_value in value.values():
            yield from _field_names(nested_value)
    elif _is_sequence(value):
        for item in value:
            yield from _field_names(item)


def _status_candidates(event: Mapping[str, Any]) -> Iterable[str]:
    yield from _statuses_from_changes(event)

    for context in _iter_mappings(event):
        for key in _STATUS_VALUE_KEYS:
            value = context.get(key)
            status = _text_or_name(value)
            if status:
                yield status


def _statuses_from_changes(event: Mapping[str, Any]) -> Iterable[str]:
    for context in _iter_mappings(event):
        for key in ("changes", "change", "changed"):
            yield from _statuses_from_change_value(context.get(key))


def _statuses_from_change_value(value: Any) -> Iterable[str]:
    if isinstance(value, Mapping):
        field_name = _text_or_name(value.get("field")) or _text_or_name(value.get("name"))
        if field_name and _is_status_field(field_name):
            status = _first_change_status(value)
            if status:
                yield status

        for key, nested_value in value.items():
            if _is_status_field(key):
                status = _first_change_status(nested_value)
                if status:
                    yield status
            else:
                yield from _statuses_from_change_value(nested_value)
    elif _is_sequence(value):
        for item in value:
            yield from _statuses_from_change_value(item)


def _first_change_status(value: Any) -> str | None:
    status = _text_or_name(value)
    if status:
        return status

    if isinstance(value, Mapping):
        for key in ("new", "newValue", "new_value", "to", "after", "current", "value", "name"):
            status = _text_or_name(value.get(key))
            if status:
                return status

    return None


def _first_text(event: Mapping[str, Any], keys: Sequence[str]) -> str | None:
    for context in _preferred_issue_contexts(event):
        for key in keys:
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _preferred_issue_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []

    for path in (
        ("triggerContext",),
        ("data", "issue"),
        ("issue",),
        ("payload", "issue"),
        ("data",),
        ("payload",),
    ):
        context = _mapping_at_path(event, path)
        if context is not None:
            contexts.append(context)

    contexts.append(event)
    return _dedupe_mappings(contexts)


def _iter_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for nested_value in value.values():
            yield from _iter_mappings(nested_value)
    elif _is_sequence(value):
        for item in value:
            yield from _iter_mappings(item)


def _mapping_at_path(value: Mapping[str, Any], path: Sequence[str]) -> Mapping[str, Any] | None:
    current: Any = value
    for key in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)

    return current if isinstance(current, Mapping) else None


def _dedupe_mappings(contexts: Iterable[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    result: list[Mapping[str, Any]] = []
    seen: set[int] = set()
    for context in contexts:
        context_id = id(context)
        if context_id not in seen:
            seen.add(context_id)
            result.append(context)
    return result


def _text_or_name(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()

    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            nested_value = value.get(key)
            if isinstance(nested_value, str) and nested_value.strip():
                return nested_value.strip()

    return None


def _is_status_field(value: Any) -> bool:
    return _compact(value) in _STATUS_FIELD_NAMES


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""

    text = _CAMEL_BOUNDARY.sub(r"\1 \2", str(value).strip())
    text = _NON_WORD.sub(" ", text)
    return _WHITESPACE.sub(" ", text).strip().lower()


def _compact(value: Any) -> str:
    return _normalize_text(value).replace(" ", "")


def _has_research_prefix(title: str) -> bool:
    return _normalize_text(title).startswith(_normalize_text(PREFIX))


def _is_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))


def main() -> int:
    """Read an automation event as JSON from stdin and print the update action."""

    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
