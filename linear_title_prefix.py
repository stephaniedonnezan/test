"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_CONTAINER_KEYS = (
    "automation_trigger_info",
    "automationTriggerInfo",
    "trigger_context",
    "triggerContext",
    "payload",
    "body",
    "data",
    "issue",
)

_TRIGGER_KEYS = (
    "trigger",
    "webhookType",
    "webhook_type",
    "action",
    "type",
    "event",
    "eventType",
    "event_type",
)

_EXPLICIT_NEW_STATUS_KEYS = (
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

_ISSUE_ID_KEYS = (
    "issueId",
    "issue_id",
    "identifier",
    "key",
    "id",
)

_TITLE_KEYS = (
    "title",
    "issueTitle",
    "issue_title",
)

_UPDATED_FIELD_KEYS = (
    "updatedFields",
    "updated_fields",
    "changedFields",
    "changed_fields",
)

_CHANGE_KEYS = (
    "changes",
    "changed",
    "updates",
    "updatedFrom",
    "updated_from",
    "previousValues",
    "previous_values",
)


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action for issues moved to To Research.

    The function is intentionally side-effect free: callers can pass the result
    to the integration layer that performs the actual Linear mutation.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _collect_contexts(event)
    if not _is_status_change_event(contexts):
        return None

    new_status = _extract_new_status(contexts)
    if not _is_target_status(new_status):
        return None

    issue_id = _extract_first_string(contexts, _ISSUE_ID_KEYS)
    title = _extract_first_string(contexts, _TITLE_KEYS)
    if not issue_id or not title:
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": _with_research_prefix(title),
    }


def _collect_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []
    seen: set[int] = set()

    def visit(value: Any) -> None:
        if not isinstance(value, Mapping):
            return

        object_id = id(value)
        if object_id in seen:
            return
        seen.add(object_id)
        contexts.append(value)

        for key in _CONTAINER_KEYS:
            visit(value.get(key))

    visit(event)
    return contexts


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    trigger_names = [
        _normalize_words(value)
        for context in contexts
        for key, value in context.items()
        if key in _TRIGGER_KEYS and isinstance(value, str)
    ]

    if any(_is_direct_status_change_trigger(name) for name in trigger_names):
        return True

    if any(_is_generic_issue_update_trigger(name) for name in trigger_names):
        return _has_status_field_change(contexts)

    return False


def _is_direct_status_change_trigger(normalized_name: str) -> bool:
    return normalized_name in {
        "status change",
        "status changed",
        "state change",
        "state changed",
        "workflow state change",
        "workflow state changed",
    }


def _is_generic_issue_update_trigger(normalized_name: str) -> bool:
    return normalized_name in {
        "update",
        "updated",
        "issue update",
        "issue updated",
        "updated issue",
    }


def _has_status_field_change(contexts: Iterable[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in _UPDATED_FIELD_KEYS:
            if _value_mentions_status_field(context.get(key)):
                return True

        for key in _CHANGE_KEYS:
            if _value_mentions_status_field(context.get(key)):
                return True

    return False


def _value_mentions_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field_name(value)

    if isinstance(value, Mapping):
        if any(_is_status_field_name(str(key)) for key in value.keys()):
            return True

        field_name = _extract_string_from_mapping(
            value,
            ("field", "fieldName", "field_name", "name", "key", "path"),
        )
        return bool(field_name and _is_status_field_name(field_name))

    if isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray, str)):
        return any(_value_mentions_status_field(item) for item in value)

    return False


def _is_status_field_name(value: str) -> bool:
    normalized = _normalize_words(value)
    compact = normalized.replace(" ", "")
    return (
        compact in {"status", "state", "workflowstate", "stateid", "workflowstateid"}
        or normalized.startswith("status ")
        or normalized.startswith("state ")
        or normalized.startswith("workflow state ")
    )


def _extract_new_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    contexts_list = list(contexts)

    for context in contexts_list:
        status = _extract_string_from_mapping(context, _EXPLICIT_NEW_STATUS_KEYS)
        if status:
            return status

    for context in contexts_list:
        for key in _CHANGE_KEYS:
            status = _extract_new_status_from_change_value(context.get(key))
            if status:
                return status

    for context in contexts_list:
        status = _extract_string_from_mapping(context, _STATUS_KEYS)
        if status:
            return status

    return None


def _extract_new_status_from_change_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key, changed_value in value.items():
            if _is_status_field_name(str(key)):
                status = _string_from_status_value(changed_value)
                if status:
                    return status

        field_name = _extract_string_from_mapping(
            value,
            ("field", "fieldName", "field_name", "name", "key", "path"),
        )
        if field_name and _is_status_field_name(field_name):
            return _extract_string_from_mapping(
                value,
                ("newValue", "new_value", "to", "after", "value", "name"),
            )

    if isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray, str)):
        for item in value:
            status = _extract_new_status_from_change_value(item)
            if status:
                return status

    return None


def _extract_first_string(
    contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]
) -> str | None:
    for context in contexts:
        value = _extract_string_from_mapping(context, keys)
        if value:
            return value
    return None


def _extract_string_from_mapping(
    mapping: Mapping[str, Any], keys: Iterable[str]
) -> str | None:
    for key in keys:
        if key in mapping:
            value = _string_from_status_value(mapping[key])
            if value:
                return value
    return None


def _string_from_status_value(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None

    if isinstance(value, Mapping):
        nested = _extract_string_from_mapping(
            value,
            ("newValue", "new_value", "to", "after", "value", "name", "title"),
        )
        if nested:
            return nested

    return None


def _is_target_status(value: str | None) -> bool:
    return _normalize_words(value) == TARGET_STATUS


def _normalize_words(value: Any) -> str:
    if value is None:
        return ""

    text = str(value).strip()
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[_-]+", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def _with_research_prefix(title: str) -> str:
    stripped = title.strip()
    if stripped.lower().startswith(PREFIX.lower()):
        return stripped
    return f"{PREFIX}: {stripped}"


def main() -> int:
    raw = sys.stdin.read()
    event = json.loads(raw) if raw.strip() else {}
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
