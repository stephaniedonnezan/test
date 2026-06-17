"""Build Linear issue title updates for Cursor research automation.

The automation should prefix a Linear issue title once an issue moves into the
"to research" status. This module is intentionally side-effect free: callers
can use the returned action to perform the actual Linear update.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELDS = {
    "newstatus",
    "newstatusname",
    "newstate",
    "newstatename",
    "newworkflowstate",
    "newworkflowstatename",
    "status",
    "statusname",
    "state",
    "statename",
    "workflowstate",
    "workflowstatename",
}
_STATUS_FIELD_ORDER = (
    "newStatus",
    "new_status",
    "newStatusName",
    "new_status_name",
    "newState",
    "new_state",
    "newStateName",
    "new_state_name",
    "newWorkflowState",
    "new_workflow_state",
    "newWorkflowStateName",
    "new_workflow_state_name",
    "status",
    "statusName",
    "status_name",
    "state",
    "stateName",
    "state_name",
    "workflowState",
    "workflow_state",
    "workflowStateName",
    "workflow_state_name",
)
_STATUS_CHANGE_FIELDS = {
    "status",
    "statusid",
    "state",
    "stateid",
    "workflowstate",
    "workflowstateid",
}
_TITLE_FIELDS = ("title", "name", "issueTitle")
_ISSUE_ID_FIELDS = ("issueId", "issue_id", "identifier", "key", "id")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to research.

    The returned shape is deliberately simple for automation runners:

    >>> build_issue_title_update({
    ...     "trigger": "status_changed",
    ...     "newStatus": "To Research",
    ...     "id": "POI-1",
    ...     "title": "Fix copy",
    ... })
    {'action': 'update_issue_title', 'issueId': 'POI-1', 'title': 'Cursor researching: Fix copy'}
    """

    if not isinstance(event, Mapping):
        return None

    context = _automation_context(event)
    if not _is_status_change_event(context, event):
        return None

    if _normalized_status(context, event) != TARGET_STATUS:
        return None

    issue = _issue_context(event, context)
    issue_id = _first_string(issue, _ISSUE_ID_FIELDS)
    title = _first_string(issue, _TITLE_FIELDS)
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _automation_context(event: Mapping[str, Any]) -> Mapping[str, Any]:
    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        return {**trigger_context, **event}
    return event


def _issue_context(event: Mapping[str, Any], context: Mapping[str, Any]) -> Mapping[str, Any]:
    """Merge likely issue payload locations, keeping outer context authoritative."""

    issue: dict[str, Any] = {}
    for candidate in (
        event.get("issue"),
        event.get("data"),
        _mapping_value(event.get("data"), "issue"),
        _mapping_value(event.get("triggerContext"), "issue"),
        _mapping_value(event.get("triggerContext"), "data"),
    ):
        if isinstance(candidate, Mapping):
            issue.update(candidate)
    issue.update(context)
    return issue


def _is_status_change_event(context: Mapping[str, Any], event: Mapping[str, Any]) -> bool:
    event_type_values = (
        context.get("trigger"),
        context.get("triggerType"),
        context.get("webhookType"),
        context.get("action"),
        context.get("type"),
        event.get("trigger"),
        event.get("action"),
        event.get("type"),
    )
    normalized_types = {_normalize(value) for value in event_type_values}

    if any(value in {"status changed", "status change", "statuschanged"} for value in normalized_types):
        return True

    if any(value in {"issue updated", "updated issue", "update", "updated"} for value in normalized_types):
        return _updated_fields_include_status(context) or _changes_include_status(context)

    return _updated_fields_include_status(context) or _changes_include_status(context)


def _updated_fields_include_status(context: Mapping[str, Any]) -> bool:
    updated_fields = context.get("updatedFields") or context.get("updated_fields") or context.get("changedFields")
    if isinstance(updated_fields, str):
        updated_fields = [updated_fields]
    if not isinstance(updated_fields, Iterable) or isinstance(updated_fields, (bytes, bytearray, Mapping)):
        return False
    return any(_status_field_name(field) in _STATUS_CHANGE_FIELDS for field in updated_fields)


def _changes_include_status(context: Mapping[str, Any]) -> bool:
    for key in ("changes", "changed", "updatedFrom", "updated_from"):
        changes = context.get(key)
        if not isinstance(changes, Mapping):
            continue
        if any(_status_field_name(field) in _STATUS_CHANGE_FIELDS for field in changes):
            return True
    return False


def _normalized_status(context: Mapping[str, Any], event: Mapping[str, Any]) -> str | None:
    for mapping in _status_contexts(context, event):
        status = _status_from_mapping(mapping)
        if status:
            return status
    return None


def _status_contexts(context: Mapping[str, Any], event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    yield context
    for candidate in (
        event.get("triggerContext"),
        event.get("data"),
        event.get("issue"),
        _mapping_value(event.get("data"), "issue"),
        _mapping_value(event.get("triggerContext"), "data"),
        _mapping_value(event.get("triggerContext"), "issue"),
    ):
        if isinstance(candidate, Mapping):
            yield candidate


def _status_from_mapping(mapping: Mapping[str, Any]) -> str | None:
    for key in _STATUS_FIELD_ORDER:
        value = mapping.get(key)
        normalized = _normalize_status_value(value)
        if normalized:
            return normalized
    for key, value in mapping.items():
        if _status_field_name(key) not in _STATUS_FIELDS:
            continue
        normalized = _normalize_status_value(value)
        if normalized:
            return normalized
    return None


def _normalize_status_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        return _normalize_status_value(
            value.get("name")
            or value.get("title")
            or value.get("label")
            or value.get("status")
            or value.get("state")
        )
    if not isinstance(value, str):
        return None
    return _normalize(value)


def _first_string(mapping: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _mapping_value(value: Any, key: str) -> Mapping[str, Any] | None:
    if isinstance(value, Mapping) and isinstance(value.get(key), Mapping):
        return value[key]
    return None


def _status_field_name(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^A-Za-z]", "", value).lower()


def _normalize(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    with_camel_spacing = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    words = re.sub(r"[^A-Za-z0-9]+", " ", with_camel_spacing).lower().split()
    return " ".join(words)


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
