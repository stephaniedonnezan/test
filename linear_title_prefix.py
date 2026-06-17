"""Build title update actions for Linear issues entering research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any

PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow_state"}
_DIRECT_STATUS_CHANGE_EVENTS = {
    "status change",
    "status changed",
    "state change",
    "state changed",
    "workflow state change",
    "workflow state changed",
}
_GENERIC_UPDATE_EVENTS = {"update", "updated", "issue update", "issue updated", "updated issue"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action for status changes to research.

    The Cursor automation payload is flat under ``triggerContext`` while Linear
    webhooks commonly nest issue data under ``data.issue``. This function
    accepts both shapes and returns ``None`` whenever no title update is needed.
    """

    if not isinstance(event, Mapping):
        return None

    context = _merged_context(event)
    if not _is_status_change_event(event, context):
        return None

    status = _new_status(event, context)
    if _normalize_words(status) != TARGET_STATUS:
        return None

    issue_id = _first_string(context, ("id", "issueId", "issue_id", "identifier", "key"))
    title = _first_string(context, ("title", "name"))
    if issue_id is None or title is None:
        return None

    stripped_title = title.strip()
    if not stripped_title or _has_prefix(stripped_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {stripped_title}",
    }


def _merged_context(event: Mapping[str, Any]) -> dict[str, Any]:
    context: dict[str, Any] = {}

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        context.update(trigger_context)

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        context.update(issue)

    data = event.get("data")
    if isinstance(data, Mapping):
        context.update(data)
        data_issue = data.get("issue")
        if isinstance(data_issue, Mapping):
            context.update(data_issue)

    # Top-level metadata such as action/type/trigger should win over nested
    # issue fields like Linear's ``type: Issue``.
    context.update(event)
    return context


def _is_status_change_event(event: Mapping[str, Any], context: Mapping[str, Any]) -> bool:
    trigger_values = {_normalize_words(value) for value in _trigger_values(event, context)}
    if trigger_values & _DIRECT_STATUS_CHANGE_EVENTS:
        return True

    if trigger_values & _GENERIC_UPDATE_EVENTS:
        return _updated_fields_include_status(event, context)

    return _updated_fields_include_status(event, context) and bool(trigger_values)


def _trigger_values(event: Mapping[str, Any], context: Mapping[str, Any]) -> Iterable[Any]:
    for source in (event, context):
        for key in ("trigger", "webhookType", "action", "type", "eventType", "triggerType"):
            value = source.get(key)
            if isinstance(value, str):
                yield value


def _updated_fields_include_status(event: Mapping[str, Any], context: Mapping[str, Any]) -> bool:
    for source in _candidate_mappings(event, context):
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            fields = source.get(key)
            if _fields_include_status(fields):
                return True

        for key in ("changes", "changed", "updatedFrom", "previousValues"):
            changes = source.get(key)
            if isinstance(changes, Mapping) and any(_is_status_field(field) for field in changes):
                return True

    return False


def _fields_include_status(fields: Any) -> bool:
    if isinstance(fields, str):
        return _is_status_field(fields)
    if isinstance(fields, Mapping):
        return any(_is_status_field(field) for field in fields)
    if isinstance(fields, Iterable):
        return any(isinstance(field, str) and _is_status_field(field) for field in fields)
    return False


def _is_status_field(value: Any) -> bool:
    normalized = _normalize_identifier(value)
    return normalized in _STATUS_FIELD_NAMES


def _new_status(event: Mapping[str, Any], context: Mapping[str, Any]) -> Any:
    for source in _candidate_mappings(event, context):
        value = _first_present(
            source,
            (
                "newStatus",
                "new_status",
                "statusName",
                "status_name",
                "newState",
                "new_state",
                "newWorkflowState",
                "new_workflow_state",
            ),
        )
        if value is not None:
            return _name_or_value(value)

    changed_status = _status_from_changes(event, context)
    if changed_status is not None:
        return changed_status

    for source in _candidate_mappings(event, context):
        for key in ("status", "state", "workflowState", "workflow_state"):
            value = source.get(key)
            if value is not None:
                return _name_or_value(value)

    return None


def _status_from_changes(event: Mapping[str, Any], context: Mapping[str, Any]) -> Any:
    for source in _candidate_mappings(event, context):
        for key in ("changes", "changed"):
            changes = source.get(key)
            if not isinstance(changes, Mapping):
                continue
            for field, value in changes.items():
                if _is_status_field(field):
                    return _changed_to_value(value)
    return None


def _changed_to_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        for key in ("to", "new", "after", "toValue", "newValue", "current"):
            if key in value:
                return _name_or_value(value[key])
    return _name_or_value(value)


def _candidate_mappings(event: Mapping[str, Any], context: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    yield context
    yield event

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        yield trigger_context

    data = event.get("data")
    if isinstance(data, Mapping):
        yield data
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            yield issue

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        yield issue


def _first_string(source: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    value = _first_present(source, keys)
    return value if isinstance(value, str) else None


def _first_present(source: Mapping[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        value = source.get(key)
        if value is not None:
            return value
    return None


def _name_or_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return _first_present(value, ("name", "title", "value", "id"))
    return value


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def _normalize_identifier(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[\s_-]+", "", value).lower()


def _normalize_words(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    value = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    value = re.sub(r"[_-]+", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip().lower()


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    json.dump(action, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
