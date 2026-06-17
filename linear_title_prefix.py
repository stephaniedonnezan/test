"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_DIRECT_STATUS_CHANGE_EVENTS = {
    "statuschange",
    "statuschanged",
    "statechange",
    "statechanged",
    "workflowstatechange",
    "workflowstatechanged",
}
_UPDATE_EVENTS = {
    "update",
    "updated",
    "issueupdate",
    "issueupdated",
    "updatedissue",
}
_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflowstate",
    "workflowstatus",
}
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
_NEW_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "newWorkflowState",
    "new_workflow_state",
    "toStatus",
    "to_status",
)
_CURRENT_STATUS_KEYS = (
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


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to research.

    The automation payload can arrive as a flat Cursor trigger context or as a
    nested Linear webhook shape. This function keeps side effects out of the
    handler and returns the action that the caller should apply.
    """

    if not isinstance(event, Mapping):
        return None

    for context in _candidate_contexts(event):
        if not _is_status_change_event(context):
            continue

        new_status = _extract_new_status(context)
        if _normalize_value(new_status) != _normalize_value(TARGET_STATUS):
            continue

        issue_id = _extract_issue_id(context)
        title = _extract_title(context)
        if issue_id is None or title is None:
            continue

        if title.lower().startswith(PREFIX.lower()):
            return None

        return {
            "action": "update_issue_title",
            "issueId": issue_id,
            "title": f"{PREFIX}: {title}",
        }

    return None


def _candidate_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        contexts.append(trigger_context)

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        contexts.append(_merge_nested_issue(event, issue))

    data = event.get("data")
    if isinstance(data, Mapping):
        data_issue = data.get("issue")
        if isinstance(data_issue, Mapping):
            contexts.append(_merge_nested_issue(data, data_issue, event))
        contexts.append(_merge_nested_issue(event, data))

    contexts.append(event)

    unique_contexts: list[Mapping[str, Any]] = []
    seen: set[int] = set()
    for context in contexts:
        context_id = id(context)
        if context_id not in seen:
            unique_contexts.append(context)
            seen.add(context_id)
    return unique_contexts


def _merge_nested_issue(
    metadata: Mapping[str, Any],
    issue: Mapping[str, Any],
    outer_metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    merged = dict(issue)
    for source in (metadata, outer_metadata):
        if not source:
            continue
        for key, value in source.items():
            if key not in {"data", "issue", "triggerContext"} and key not in merged:
                merged[key] = value
    return merged


def _is_status_change_event(context: Mapping[str, Any]) -> bool:
    trigger_values = [
        _normalize_value(context.get(key))
        for key in _TRIGGER_KEYS
        if context.get(key) is not None
    ]

    if any(value in _DIRECT_STATUS_CHANGE_EVENTS for value in trigger_values):
        return True

    return any(value in _UPDATE_EVENTS for value in trigger_values) and _updated_fields_include_status(
        context
    )


def _updated_fields_include_status(context: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        if _contains_status_field(context.get(key)):
            return True

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        return any(_normalize_value(key) in _STATUS_FIELD_NAMES for key in changes.keys())

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_value(value) in _STATUS_FIELD_NAMES

    if isinstance(value, Mapping):
        for field_key in ("field", "name", "key"):
            field_name = value.get(field_key)
            if isinstance(field_name, str) and _normalize_value(field_name) in _STATUS_FIELD_NAMES:
                return True
        return any(_normalize_value(key) in _STATUS_FIELD_NAMES for key in value.keys())

    if isinstance(value, list | tuple | set):
        return any(_contains_status_field(item) for item in value)

    return False


def _extract_new_status(context: Mapping[str, Any]) -> str | None:
    for key in _NEW_STATUS_KEYS:
        status = _string_from_status_value(context.get(key))
        if status is not None:
            return status

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        for key, value in changes.items():
            if _normalize_value(key) in _STATUS_FIELD_NAMES:
                changed_status = _string_from_change(value)
                if changed_status is not None:
                    return changed_status

    for key in ("updatedFields", "updated_fields"):
        status = _string_from_updated_fields(context.get(key))
        if status is not None:
            return status

    for key in _CURRENT_STATUS_KEYS:
        status = _string_from_status_value(context.get(key))
        if status is not None:
            return status

    return None


def _string_from_change(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("new", "after", "to", "newValue", "new_value"):
            status = _string_from_status_value(value.get(key))
            if status is not None:
                return status

    return _string_from_status_value(value)


def _string_from_updated_fields(value: Any) -> str | None:
    if not isinstance(value, list | tuple | set):
        return None

    for item in value:
        if not isinstance(item, Mapping):
            continue

        field_name = item.get("field") or item.get("name") or item.get("key")
        if not isinstance(field_name, str) or _normalize_value(field_name) not in _STATUS_FIELD_NAMES:
            continue

        for key in ("newValue", "new_value", "new", "after", "to", "value"):
            status = _string_from_status_value(item.get(key))
            if status is not None:
                return status

    return None


def _string_from_status_value(value: Any) -> str | None:
    if isinstance(value, str):
        normalized = value.strip()
        return normalized or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "label", "value"):
            status = _string_from_status_value(value.get(key))
            if status is not None:
                return status

    return None


def _extract_issue_id(context: Mapping[str, Any]) -> str | None:
    for key in _ISSUE_ID_KEYS:
        value = context.get(key)
        if isinstance(value, str):
            issue_id = value.strip()
            if issue_id:
                return issue_id

    return None


def _extract_title(context: Mapping[str, Any]) -> str | None:
    for key in ("title", "name"):
        value = context.get(key)
        if isinstance(value, str):
            title = value.strip()
            if title:
                return title

    return None


def _normalize_value(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return re.sub(r"[^a-z0-9]+", "", spaced.lower())


def main() -> int:
    event = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(event), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
