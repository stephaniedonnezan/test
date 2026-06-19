"""Build Linear issue title updates for research-status automations."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_CAMEL_CASE_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_NON_WORD_RUN = re.compile(r"[^A-Za-z0-9]+")
_STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow_state"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return the title update needed for Linear research status changes.

    The returned action is intentionally side-effect free so automation runners can
    decide how to apply it to Linear.
    """

    if not isinstance(event, Mapping):
        return None

    context = _automation_context(event)
    if not _is_status_change_event(event, context):
        return None

    if _normalized_status(_new_status(event, context)) != TARGET_STATUS:
        return None

    issue_id = _clean_text(_first_value(context, "issueId", "issue_id", "id", "identifier", "key"))
    title = _clean_text(_first_value(context, "title"))
    if not issue_id or not title:
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": _prefixed_title(title),
    }


def _automation_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common Cursor and Linear webhook nesting into one lookup context."""

    context: dict[str, Any] = {}
    for item in _walk_mappings(event):
        context.update(item)
    return context


def _walk_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for nested in value.values():
            yield from _walk_mappings(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _walk_mappings(nested)


def _is_status_change_event(event: Mapping[str, Any], context: Mapping[str, Any]) -> bool:
    trigger_values = [
        value
        for item in _walk_mappings(event)
        for key, value in item.items()
        if _normalized_key(key) in {"trigger", "action", "type", "webhooktype", "webhook_type"}
    ]
    normalized_triggers = {_normalized_status(value) for value in trigger_values}

    if normalized_triggers & {
        "status changed",
        "status change",
        "state changed",
        "state change",
        "workflow state changed",
        "workflow state change",
    }:
        return True

    if normalized_triggers & {"update", "updated", "issue updated", "updated issue"}:
        return _updated_fields_include_status(event, context)

    return False


def _updated_fields_include_status(event: Mapping[str, Any], context: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        fields = _first_value(context, key)
        if _fields_include_status(fields):
            return True

    changes = _first_value(context, "changes", "changed")
    if isinstance(changes, Mapping):
        return any(_normalized_key(key) in _STATUS_FIELD_NAMES for key in changes)

    for item in _walk_mappings(event):
        for key, value in item.items():
            if _normalized_key(key) in {"updatedfields", "updated_fields", "changedfields", "changed_fields"}:
                if _fields_include_status(value):
                    return True

    return False


def _fields_include_status(fields: Any) -> bool:
    if isinstance(fields, str):
        return _normalized_key(fields) in _STATUS_FIELD_NAMES
    if isinstance(fields, Iterable):
        return any(_fields_include_status(field) for field in fields)
    return False


def _new_status(event: Mapping[str, Any], context: Mapping[str, Any]) -> Any:
    explicit_status = _first_value(
        context,
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "newWorkflowState",
        "new_workflow_state",
        "statusName",
        "status_name",
        "stateName",
        "state_name",
    )
    if explicit_status is not None:
        return explicit_status

    for item in _walk_mappings(event):
        for key in ("status", "state", "workflowState", "workflow_state"):
            value = item.get(key)
            if isinstance(value, Mapping):
                name = value.get("name")
                if name is not None:
                    return name
            elif value is not None:
                return value

    return None


def _first_value(context: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in context and context[key] is not None:
            return context[key]
    return None


def _prefixed_title(title: str) -> str:
    if title.casefold().startswith(TITLE_PREFIX.casefold()):
        return title
    return f"{TITLE_PREFIX}: {title}"


def _clean_text(value: Any) -> str | None:
    if isinstance(value, str):
        text = value.strip()
        return text or None
    return None


def _normalized_status(value: Any) -> str | None:
    text = _clean_text(value)
    if text is None:
        return None
    text = _CAMEL_CASE_BOUNDARY.sub(" ", text)
    return _NON_WORD_RUN.sub(" ", text).strip().casefold()


def _normalized_key(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return _NON_WORD_RUN.sub("", value).casefold()


def main() -> int:
    update = build_issue_title_update(json.load(sys.stdin))
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
