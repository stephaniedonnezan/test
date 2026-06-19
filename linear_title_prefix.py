"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_TRIGGER_KEYS = (
    "trigger",
    "webhookType",
    "webhook_type",
    "action",
    "type",
    "eventType",
    "event_type",
)
_ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "key", "id")
_TITLE_KEYS = ("title",)
_EXPLICIT_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "newWorkflowState",
    "new_workflow_state",
    "statusName",
    "status_name",
)
_STATUS_FALLBACK_KEYS = ("status", "state", "workflowState", "workflow_state")
_UPDATED_FIELD_KEYS = (
    "updatedFields",
    "updated_fields",
    "changedFields",
    "changed_fields",
)
_STATUS_FIELD_NAMES = {"status", "state", "workflow state", "workflowstate"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to research."""

    if not isinstance(event, Mapping):
        return None

    contexts = _candidate_contexts(event)
    if not _is_status_change(contexts):
        return None

    status = _find_status(contexts)
    if _normalize_text(status) != TARGET_STATUS:
        return None

    issue_id = _find_first_string(contexts, _ISSUE_ID_KEYS)
    title = _find_first_string(contexts, _TITLE_KEYS)
    if not issue_id or not title:
        return None

    if title.casefold().startswith(TITLE_PREFIX.casefold()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _candidate_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []
    seen: set[int] = set()

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and id(value) not in seen:
            seen.add(id(value))
            contexts.append(value)

    automation_info = _mapping_at(event, "automation_trigger_info")
    automation_info = automation_info or _mapping_at(event, "automationTriggerInfo")
    trigger_context = _mapping_at(event, "triggerContext")
    trigger_context = trigger_context or _mapping_at(event, "trigger_context")
    automation_trigger_context = None
    if automation_info is not None:
        automation_trigger_context = _mapping_at(automation_info, "triggerContext")
        automation_trigger_context = automation_trigger_context or _mapping_at(
            automation_info, "trigger_context"
        )

    data = _mapping_at(event, "data")
    issue = _mapping_at(event, "issue")
    data_issue = _mapping_at(data, "issue") if data is not None else None

    # Prefer issue-shaped contexts for id/title while still keeping outer metadata
    # available for trigger and status checks.
    add(automation_trigger_context)
    add(trigger_context)
    add(data_issue)
    add(issue)
    add(data)
    add(event)
    add(automation_info)
    return contexts


def _is_status_change(contexts: list[Mapping[str, Any]]) -> bool:
    trigger_values = [
        value
        for context in contexts
        for key in _TRIGGER_KEYS
        if (value := _string_value(context.get(key)))
    ]

    if any(_is_direct_status_trigger(value) for value in trigger_values):
        return True

    if any(_is_issue_update_trigger(value) for value in trigger_values):
        return _updated_fields_include_status(contexts)

    return False


def _is_direct_status_trigger(value: str) -> bool:
    normalized = _normalize_text(value)
    return normalized in {
        "status change",
        "status changed",
        "state change",
        "state changed",
        "workflow state change",
        "workflow state changed",
    }


def _is_issue_update_trigger(value: str) -> bool:
    normalized = _normalize_text(value)
    return normalized in {
        "update",
        "updated",
        "issue update",
        "issue updated",
        "updated issue",
    }


def _updated_fields_include_status(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in _UPDATED_FIELD_KEYS:
            if _field_values_include_status(context.get(key)):
                return True

        changes = context.get("changes")
        if isinstance(changes, Mapping):
            if any(_is_status_field(field_name) for field_name in changes):
                return True

    return False


def _field_values_include_status(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)

    if isinstance(value, Mapping):
        field_name = _find_first_string(
            [value], ("name", "field", "key", "fieldName", "field_name")
        )
        if field_name and _is_status_field(field_name):
            return True
        return any(_field_values_include_status(item) for item in value.values())

    if isinstance(value, (list, tuple, set)):
        return any(_field_values_include_status(item) for item in value)

    return False


def _is_status_field(value: Any) -> bool:
    normalized = _normalize_text(_string_value(value))
    return normalized in _STATUS_FIELD_NAMES


def _find_status(contexts: list[Mapping[str, Any]]) -> str | None:
    for key_group in (_EXPLICIT_STATUS_KEYS,):
        status = _find_named_value(contexts, key_group)
        if status:
            return status

    status_from_changes = _find_status_in_changes(contexts)
    if status_from_changes:
        return status_from_changes

    return _find_named_value(contexts, _STATUS_FALLBACK_KEYS)


def _find_status_in_changes(contexts: list[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        changes = context.get("changes")
        if not isinstance(changes, Mapping):
            continue

        for key in _STATUS_FALLBACK_KEYS:
            if key not in changes:
                continue
            value = changes[key]
            if isinstance(value, Mapping):
                status = _find_named_value(
                    [value],
                    ("to", "new", "after", "newValue", "new_value", "name"),
                )
                if status:
                    return status
            else:
                status = _string_value(value)
                if status:
                    return status

    return None


def _find_named_value(
    contexts: list[Mapping[str, Any]], keys: tuple[str, ...]
) -> str | None:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if isinstance(value, Mapping):
                value = _find_first_string([value], ("name", "title", "label"))
            else:
                value = _string_value(value)
            if value:
                return value
    return None


def _find_first_string(
    contexts: list[Mapping[str, Any]], keys: tuple[str, ...]
) -> str | None:
    for context in contexts:
        for key in keys:
            value = _string_value(context.get(key))
            if value:
                return value
    return None


def _mapping_at(context: Mapping[str, Any] | None, key: str) -> Mapping[str, Any] | None:
    if context is None:
        return None
    value = context.get(key)
    return value if isinstance(value, Mapping) else None


def _string_value(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _normalize_text(value: str | None) -> str:
    if value is None:
        return ""

    separated = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value.strip())
    normalized = re.sub(r"[^A-Za-z0-9]+", " ", separated).casefold()
    return " ".join(normalized.split())


def main() -> int:
    event = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(event), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
