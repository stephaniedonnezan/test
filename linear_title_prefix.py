"""Build Linear issue-title updates for Cursor research automation.

The automation is intentionally side-effect free: callers pass in a Linear or
Cursor webhook payload and receive the issue-title update they should perform.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"

_DIRECT_STATUS_CHANGE_EVENTS = {
    "status change",
    "status changed",
    "status update",
    "status updated",
    "state change",
    "state changed",
    "workflow state change",
    "workflow state changed",
}
_ISSUE_UPDATE_EVENTS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}
_EXPLICIT_NEW_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "newWorkflowState",
    "new_workflow_state",
    "toStatus",
    "to_status",
    "targetStatus",
    "target_status",
    "statusName",
    "status_name",
    "stateName",
    "state_name",
    "workflowStateName",
    "workflow_state_name",
)
_CURRENT_STATUS_KEYS = ("status", "state", "workflowState", "workflow_state")
_ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "key", "id")
_TITLE_KEYS = ("title", "issueTitle", "issue_title", "name", "summary")
_TRIGGER_KEYS = (
    "trigger",
    "webhookType",
    "webhook_type",
    "action",
    "type",
    "event",
    "eventType",
)
_UPDATE_FIELD_KEYS = (
    "updatedFields",
    "updated_fields",
    "changedFields",
    "changed_fields",
)
_CHANGE_KEYS = ("changes", "updatedFrom", "updated_from")
_NEW_STATUS_CHANGE_KEYS = ("changes",)
_STATUS_CONTAINER_KEYS = {"status", "state", "workflowState", "workflow_state"}
_STATUS_FIELD_NAMES = {
    "status",
    "statusid",
    "state",
    "stateid",
    "workflow",
    "workflowid",
    "workflowstate",
    "workflowstateid",
    "workflowstatus",
    "workflowstatusid",
}
_SKIP_WALK_KEYS = {
    "before",
    "changes",
    "history",
    "old",
    "previous",
    "updatedFrom",
    "updated_from",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return the title-update action for an issue moved to research."""

    if not isinstance(event, Mapping):
        return None

    contexts = list(_walk_mappings(event))
    if not _is_status_change_event(contexts):
        return None

    new_status = _find_new_status(contexts)
    if _normalize_words(new_status) != TARGET_STATUS:
        return None

    issue_id, title = _find_issue_fields(contexts)
    if not issue_id or not title:
        return None

    stripped_title = title.strip()
    if not stripped_title or _has_research_prefix(stripped_title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {stripped_title}",
    }


def handle_issue_status_changed(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Compatibility wrapper for automation entrypoints."""

    return build_issue_title_update(event)


def _walk_mappings(root: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely issue and trigger mappings in priority order."""

    seen: set[int] = set()
    queue: list[Mapping[str, Any]] = []

    def enqueue(value: Any) -> None:
        if isinstance(value, Mapping) and id(value) not in seen:
            seen.add(id(value))
            queue.append(value)

    automation_info = root.get("automation_trigger_info") or root.get(
        "automationTriggerInfo"
    )
    if isinstance(automation_info, Mapping):
        enqueue(automation_info.get("triggerContext"))
        enqueue(automation_info.get("trigger_context"))
        enqueue(automation_info)

    enqueue(root.get("triggerContext"))
    enqueue(root.get("trigger_context"))

    data = root.get("data")
    if isinstance(data, Mapping):
        enqueue(data.get("issue"))
        enqueue(data.get("node"))
        enqueue(data.get("object"))
        enqueue(data)

    enqueue(root.get("issue"))
    enqueue(root.get("node"))
    enqueue(root.get("object"))
    enqueue(root.get("payload"))
    enqueue(root)

    index = 0
    while index < len(queue):
        mapping = queue[index]
        index += 1
        yield mapping

        for key, value in mapping.items():
            if key in _SKIP_WALK_KEYS or key in _STATUS_CONTAINER_KEYS:
                continue
            if isinstance(value, Mapping):
                enqueue(value)
            elif isinstance(value, list):
                for item in value:
                    enqueue(item)


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    has_issue_update_event = False
    has_status_field_change = False

    for context in contexts:
        for key in _TRIGGER_KEYS:
            normalized = _normalize_words(_string_value(context.get(key)))
            if normalized in _DIRECT_STATUS_CHANGE_EVENTS:
                return True
            if normalized in _ISSUE_UPDATE_EVENTS:
                has_issue_update_event = True

        if _updated_fields_include_status(context) or _changes_include_status(context):
            has_status_field_change = True

    return has_issue_update_event and has_status_field_change


def _updated_fields_include_status(context: Mapping[str, Any]) -> bool:
    return any(
        _status_from_field_updates(context.get(key)) is not None
        or _field_collection_includes_status(context.get(key))
        for key in _UPDATE_FIELD_KEYS
    )


def _field_collection_includes_status(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field_name(value)
    if isinstance(value, Mapping):
        if any(_is_status_field_name(key) for key in value):
            return True
        return any(
            _is_status_field_name(value.get(key)) for key in ("field", "name", "key")
        )
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes, Mapping)):
        return any(_field_collection_includes_status(item) for item in value)
    return False


def _changes_include_status(context: Mapping[str, Any]) -> bool:
    return any(_status_from_changes(context.get(key)) is not None for key in _CHANGE_KEYS)


def _status_from_changes(value: Any) -> Any:
    if isinstance(value, Mapping):
        for key, change in value.items():
            if _is_status_field_name(key):
                return _new_value_from_change(change)
        return None

    if isinstance(value, str):
        return None

    if isinstance(value, Iterable):
        for item in value:
            if not isinstance(item, Mapping):
                continue
            field_name = _first_mapping_text(item, ("field", "name", "key"))
            if field_name and _is_status_field_name(field_name):
                return _new_value_from_change(item)

    return None


def _status_from_field_updates(value: Any) -> Any:
    if isinstance(value, Mapping):
        for key, change in value.items():
            if _is_status_field_name(key):
                return _new_value_from_change(change)

        field_name = _first_mapping_text(value, ("field", "name", "key"))
        if field_name and _is_status_field_name(field_name):
            return _new_value_from_change(value)

        return None

    if isinstance(value, str):
        return None

    if isinstance(value, Iterable):
        for item in value:
            status = _status_from_field_updates(item)
            if status is not None:
                return status

    return None


def _new_value_from_change(change: Any) -> Any:
    if isinstance(change, Mapping):
        for key in ("to", "new", "newValue", "new_value", "after", "current"):
            if key in change:
                return change[key]
    return change


def _find_new_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        for key in _EXPLICIT_NEW_STATUS_KEYS:
            status = _status_name(context.get(key))
            if status:
                return status

    for context in contexts:
        for key in _UPDATE_FIELD_KEYS:
            status = _status_name(_status_from_field_updates(context.get(key)))
            if status:
                return status

    for context in contexts:
        for key in _NEW_STATUS_CHANGE_KEYS:
            status = _status_name(_status_from_changes(context.get(key)))
            if status:
                return status

    for context in contexts:
        for key in _CURRENT_STATUS_KEYS:
            status = _status_name(context.get(key))
            if status:
                return status

    return None


def _status_name(value: Any) -> str | None:
    if isinstance(value, Mapping):
        return _first_mapping_text(value, ("name", "title", "label"))
    return _string_value(value)


def _find_issue_fields(contexts: Iterable[Mapping[str, Any]]) -> tuple[str | None, str | None]:
    fallback_issue_id: str | None = None

    for context in contexts:
        issue_id = _find_direct_string(context, _ISSUE_ID_KEYS)
        title = _find_direct_string(context, _TITLE_KEYS)

        if issue_id and title:
            return issue_id, title
        if issue_id and fallback_issue_id is None:
            fallback_issue_id = issue_id
        if title and fallback_issue_id:
            return fallback_issue_id, title

    return fallback_issue_id, None


def _find_direct_string(context: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for key in keys:
        value = _string_value(context.get(key))
        if value:
            return value
    return None


def _first_mapping_text(mapping: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for key in keys:
        text = _string_value(mapping.get(key))
        if text:
            return text
    return None


def _is_status_field_name(value: Any) -> bool:
    text = _string_value(value)
    if not text:
        return False
    return _normalize_field_name(text) in _STATUS_FIELD_NAMES


def _has_research_prefix(title: str) -> bool:
    return re.match(r"^\s*cursor researching\b", title, flags=re.IGNORECASE) is not None


def _normalize_words(value: str | None) -> str | None:
    if value is None:
        return None
    value = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    value = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", value)
    value = re.sub(r"[^A-Za-z0-9]+", " ", value)
    return " ".join(value.casefold().split())


def _normalize_field_name(value: str) -> str:
    normalized = _normalize_words(value) or ""
    return normalized.replace(" ", "")


def _string_value(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    if isinstance(value, int):
        return str(value)
    return None


def main() -> int:
    try:
        event = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        print("null")
        return 1

    update = build_issue_title_update(event)
    print(json.dumps(update, sort_keys=True) if update else "null")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
