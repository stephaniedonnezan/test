"""Build title-update actions for Linear issues entering research status."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {
    "status",
    "statusid",
    "statusname",
    "state",
    "stateid",
    "statename",
    "workflowstate",
    "workflowstateid",
    "workflowstatename",
}
EXPLICIT_NEW_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "newWorkflowState",
    "new_workflow_state",
    "toStatus",
    "to_status",
    "toState",
    "to_state",
)
ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "key", "id")
ISSUE_TITLE_KEYS = ("title",)


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue-title update action when an issue moves to To Research.

    The handler accepts both Cursor automation trigger payloads and Linear-style
    issue update webhooks. It returns None for events that do not represent a
    status change to the target research status, or for titles already carrying
    the prefix.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    if _normalize_words(_extract_new_status(event)) != TARGET_STATUS:
        return None

    issue_id = _first_string(_issue_contexts(event), ISSUE_ID_KEYS)
    title = _first_string(_issue_contexts(event), ISSUE_TITLE_KEYS)
    if not issue_id or not title:
        return None

    issue_id = issue_id.strip()
    title = title.strip()
    if not issue_id or not title or _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    trigger_values = list(_values_for_keys(_metadata_contexts(event), ("trigger",)))
    if any(_is_direct_status_change(value) for value in trigger_values):
        return True

    # Explicit non-status Cursor triggers should not fire just because they carry
    # issue metadata with a current status.
    if trigger_values and not any(_is_generic_update(value) for value in trigger_values):
        return False

    action_values = list(_values_for_keys(_metadata_contexts(event), ("action", "type", "webhookType", "webhook_type")))
    if any(_is_direct_status_change(value) for value in action_values):
        return True

    if any(_is_generic_update(value) for value in action_values) and _has_status_change_indicator(event):
        return True

    return _has_status_change_indicator(event) and not action_values


def _extract_new_status(event: Mapping[str, Any]) -> str:
    for value in _values_for_keys(_all_contexts(event), EXPLICIT_NEW_STATUS_KEYS):
        status = _status_name(value)
        if status:
            return status

    for value in _change_values(event):
        status = _status_name(value)
        if status:
            return status

    for context in _all_contexts(event):
        for key in ("status", "state", "workflowState", "workflow_state"):
            value = _get_case_insensitive(context, key)
            status = _status_name(value)
            if status:
                return status

    return ""


def _has_status_change_indicator(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized_key = _normalize_key(key)
            if normalized_key in ("updatedfrom", "previousvalues") and isinstance(child, Mapping):
                if any(_normalize_key(changed_key) in STATUS_FIELD_NAMES for changed_key in child):
                    return True

            if normalized_key in ("updatedfields", "changedfields") and _fields_include_status(child):
                return True

            if normalized_key in ("changes", "changed", "diff") and _changes_include_status(child):
                return True

            if _has_status_change_indicator(child):
                return True

    if isinstance(value, list):
        return any(_has_status_change_indicator(item) for item in value)

    return False


def _changes_include_status(value: Any) -> bool:
    if isinstance(value, Mapping):
        if any(_normalize_key(key) in STATUS_FIELD_NAMES for key in value):
            return True

        field_name = _first_string((value,), ("field", "fieldName", "name", "property"))
        if field_name and _normalize_key(field_name) in STATUS_FIELD_NAMES:
            return True

        return any(_changes_include_status(child) for child in value.values())

    if isinstance(value, list):
        return any(_changes_include_status(item) for item in value)

    return False


def _fields_include_status(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_key(value) in STATUS_FIELD_NAMES

    if isinstance(value, Mapping):
        return any(
            _normalize_key(key) in STATUS_FIELD_NAMES or _fields_include_status(child)
            for key, child in value.items()
        )

    if isinstance(value, Iterable):
        return any(_fields_include_status(item) for item in value)

    return False


def _change_values(event: Mapping[str, Any]) -> Iterable[Any]:
    for context in _all_contexts(event):
        for key in ("changes", "changed", "diff"):
            changes = _get_case_insensitive(context, key)
            yield from _status_change_values(changes)


def _status_change_values(value: Any) -> Iterable[Any]:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if _normalize_key(key) in STATUS_FIELD_NAMES:
                yield child
                yield from _new_values(child)
            else:
                field_name = _first_string((child,), ("field", "fieldName", "name", "property"))
                if field_name and _normalize_key(field_name) in STATUS_FIELD_NAMES:
                    yield from _new_values(child)
                yield from _status_change_values(child)

    if isinstance(value, list):
        for item in value:
            yield from _status_change_values(item)


def _new_values(value: Any) -> Iterable[Any]:
    if isinstance(value, Mapping):
        for key in ("to", "after", "new", "newValue", "new_value", "value", "name"):
            child = _get_case_insensitive(value, key)
            if child is not None:
                yield child
    elif isinstance(value, list) and value:
        yield value[-1]
    else:
        yield value


def _status_name(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()

    if isinstance(value, Mapping):
        for key in ("name", "title", "value", "to", "after", "new", "newValue", "new_value"):
            child = _get_case_insensitive(value, key)
            status = _status_name(child)
            if status:
                return status

    return ""


def _issue_contexts(event: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    contexts: list[Mapping[str, Any]] = []

    automation_info = event.get("automation_trigger_info")
    if isinstance(automation_info, Mapping):
        trigger_context = automation_info.get("triggerContext")
        if isinstance(trigger_context, Mapping):
            contexts.append(trigger_context)

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        contexts.append(trigger_context)

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        contexts.append(issue)

    data = event.get("data")
    if isinstance(data, Mapping):
        data_issue = data.get("issue")
        if isinstance(data_issue, Mapping):
            contexts.append(data_issue)
        contexts.append(data)

    contexts.append(event)
    return tuple(contexts)


def _metadata_contexts(event: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    contexts: list[Mapping[str, Any]] = [event]

    automation_info = event.get("automation_trigger_info")
    if isinstance(automation_info, Mapping):
        contexts.append(automation_info)
        trigger_context = automation_info.get("triggerContext")
        if isinstance(trigger_context, Mapping):
            contexts.append(trigger_context)

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        contexts.append(trigger_context)

    data = event.get("data")
    if isinstance(data, Mapping):
        contexts.append(data)

    return tuple(contexts)


def _all_contexts(event: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    ordered: list[Mapping[str, Any]] = []
    for context in (*_metadata_contexts(event), *_issue_contexts(event)):
        if context not in ordered:
            ordered.append(context)
    return tuple(ordered)


def _values_for_keys(contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> Iterable[Any]:
    for context in contexts:
        for key in keys:
            value = _get_case_insensitive(context, key)
            if value is not None:
                yield value


def _first_string(contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str:
    for value in _values_for_keys(contexts, keys):
        if isinstance(value, str) and value.strip():
            return value
        if isinstance(value, int):
            return str(value)
    return ""


def _get_case_insensitive(mapping: Mapping[str, Any], key: str) -> Any:
    normalized = _normalize_key(key)
    for existing_key, value in mapping.items():
        if _normalize_key(existing_key) == normalized:
            return value
    return None


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def _is_direct_status_change(value: Any) -> bool:
    normalized = _normalize_words(value)
    words = set(normalized.split())
    return "changed" in words and bool(words & {"status", "state", "workflowstate", "workflow"})


def _is_generic_update(value: Any) -> bool:
    normalized = _normalize_words(value)
    return normalized in {"update", "updated", "issue update", "issue updated", "updated issue"}


def _normalize_words(value: Any) -> str:
    if value is None:
        return ""
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", str(value))
    text = re.sub(r"[^a-zA-Z0-9]+", " ", text).strip().lower()
    return re.sub(r"\s+", " ", text)


def _normalize_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", _normalize_words(value))


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
