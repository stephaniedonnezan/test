"""Build Linear issue-title updates for research status changes.

The automation receives slightly different payload shapes depending on which
Cursor/Linear trigger produced the event. This module keeps the behavior small
and deterministic: only status changes to "to research" produce a title update.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}
STATUS_CHANGE_FIELDS = STATUS_FIELDS | {
    "statusid",
    "status_id",
    "stateid",
    "state_id",
    "workflowstateid",
    "workflow_state_id",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update action when an issue enters research.

    The returned value is intentionally side-effect free so the surrounding
    automation can decide how to apply it:

    {
        "action": "update_issue_title",
        "issueId": "POI-123",
        "title": "Cursor researching: Existing title",
    }
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _candidate_contexts(event)
    if not _is_status_change_event(contexts):
        return None

    status = _extract_new_status(contexts)
    if _normalize_words(status) != TARGET_STATUS:
        return None

    issue_id = _extract_first_string(contexts, ("issueId", "issue_id", "identifier", "key"))
    if not issue_id:
        issue_id = _extract_first_string(contexts, ("id",))
    title = _extract_first_string(contexts, ("title", "name"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _candidate_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Collect payload maps in a stable order from common Cursor/Linear shapes."""

    contexts: list[Mapping[str, Any]] = []
    seen: set[int] = set()

    pending: list[Any] = [event]
    while pending:
        value = pending.pop(0)
        if not isinstance(value, Mapping) or id(value) in seen:
            continue
        seen.add(id(value))
        contexts.append(value)
        for key in ("issue", "data", "triggerContext", "payload"):
            pending.append(value.get(key))

    return contexts


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    trigger_values = _values_for_keys(contexts, ("trigger", "webhookType", "action", "type", "event"))
    normalized_triggers = {_normalize_words(value) for value in trigger_values}

    if normalized_triggers & {"status changed", "status change", "state changed", "workflow state changed"}:
        return True

    updated_issue_triggers = {"issue updated", "updated issue", "update", "updated"}
    if normalized_triggers & updated_issue_triggers:
        return _has_status_change_field(contexts)

    return False


def _extract_new_status(contexts: list[Mapping[str, Any]]) -> str | None:
    explicit_keys = (
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
        "workflowStateName",
        "workflow_state_name",
    )
    status = _extract_first_string(contexts, explicit_keys)
    if status:
        return status

    status = _extract_status_from_changes(contexts)
    if status:
        return status

    return _extract_first_status_value(contexts, ("status", "state", "workflowState", "workflow_state"))


def _extract_status_from_changes(contexts: list[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        for key in ("changes", "changed", "updatedFields"):
            value = context.get(key)
            status = _status_from_change_container(value)
            if status:
                return status
    return None


def _status_from_change_container(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key, change in value.items():
            if _normalize_key(key) not in STATUS_FIELDS:
                continue
            status = _status_from_change_value(change)
            if status:
                return status
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, Mapping):
                field = _extract_first_string([item], ("field", "name", "key"))
                if field and _normalize_key(field) in STATUS_FIELDS:
                    status = _status_from_change_value(item)
                    if status:
                        return status
            elif isinstance(item, str) and _normalize_key(item) in STATUS_FIELDS:
                return None
    return None


def _status_from_change_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        status = _extract_first_status_value(
            [value],
            ("to", "toValue", "newValue", "new", "after", "value", "name", "title"),
        )
        if status:
            return status
    elif isinstance(value, str):
        return value
    return None


def _extract_first_status_value(contexts: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
            if isinstance(value, Mapping):
                nested = _extract_first_string([value], ("name", "title", "label"))
                if nested:
                    return nested
    return None


def _extract_first_string(contexts: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _values_for_keys(contexts: list[Mapping[str, Any]], keys: tuple[str, ...]) -> list[str]:
    values: list[str] = []
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                values.append(value)
    return values


def _has_status_change_field(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "changes", "changed"):
            value = context.get(key)
            if _contains_status_field(value):
                return True
    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(_normalize_key(key) in STATUS_CHANGE_FIELDS for key in value)
    if isinstance(value, list):
        for item in value:
            if isinstance(item, str) and _normalize_key(item) in STATUS_CHANGE_FIELDS:
                return True
            if isinstance(item, Mapping):
                field = _extract_first_string([item], ("field", "name", "key"))
                if field and _normalize_key(field) in STATUS_CHANGE_FIELDS:
                    return True
    return False


def _normalize_words(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def _normalize_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", _normalize_words(value))


def main() -> int:
    """Read a JSON event from stdin and print the title update action, if any."""

    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 2

    result = build_issue_title_update(event)
    if result is not None:
        print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
