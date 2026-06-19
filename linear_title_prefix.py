"""Build Linear issue title updates for research status changes.

The module is intentionally small and dependency-free so it can be used as a
JSON-in/JSON-out step by webhook automations.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = ("status", "state", "workflowState", "workflow_state")
NEW_STATUS_FIELDS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "newWorkflowState",
    "new_workflow_state",
    *STATUS_FIELDS,
)
STATUS_CHANGE_TRIGGERS = {
    "status changed",
    "status change",
    "status update",
    "status updated",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
}
GENERIC_UPDATE_TRIGGERS = {
    "issue updated",
    "updated issue",
    "update",
    "updated",
}
CHANGE_TO_FIELDS = (
    "new",
    "to",
    "after",
    "current",
    "newValue",
    "toValue",
    "afterValue",
    "currentValue",
)
ISSUE_ID_FIELDS = ("issueId", "issue_id", "identifier", "key", "id")
TITLE_FIELDS = ("title", "name")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title-update action when an issue enters research."""

    if not isinstance(event, Mapping) or not _is_status_change_event(event):
        return None

    status = _new_status(event)
    if _normalize(status) != TARGET_STATUS:
        return None

    issue_id = _first_value(event, ISSUE_ID_FIELDS)
    title = _first_value(event, TITLE_FIELDS)
    if not issue_id or not title:
        return None

    issue_id = issue_id.strip()
    title = title.strip()
    if not issue_id or not title or _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    for context in _candidate_contexts(event):
        triggers = {
            normalized
            for normalized in (
                _normalize(value)
                for value in _direct_values(
                    context,
                    ("trigger", "type", "webhookType", "webhook_type", "action"),
                )
            )
            if normalized
        }

        if triggers & STATUS_CHANGE_TRIGGERS:
            return True

        if triggers & GENERIC_UPDATE_TRIGGERS and _status_changed(context):
            return True

        if not triggers and _status_changed(context):
            return True

    return False


def _new_status(event: Mapping[str, Any]) -> str | None:
    for context in _candidate_contexts(event):
        status = _value_name(_first_direct_value(context, NEW_STATUS_FIELDS))
        if status:
            return status

        for collection_key in ("changes",):
            status = _status_from_change_collection(_get_value(context, (collection_key,)))
            if status:
                return status

        fields = _get_value(context, ("updatedFields",))
        if fields is None:
            fields = _get_value(context, ("changedFields",))
        if _mentions_status_field(fields):
            status = _value_name(_first_direct_value(context, STATUS_FIELDS))
            if status:
                return status

        issue_status = _status_from_issue(context)
        if issue_status:
            return issue_status

    return None


def _first_value(event: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for context in _candidate_contexts(event):
        value = _value_name(_first_direct_value(context, keys))
        if value:
            return value
    return None


def _candidate_contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    yield event

    for path in (
        ("triggerContext",),
        ("trigger_context",),
        ("payload",),
        ("payload", "issue"),
        ("data",),
        ("data", "issue"),
        ("issue",),
    ):
        value = _get_value(event, path)
        if isinstance(value, Mapping):
            yield value


def _status_changed(context: Mapping[str, Any]) -> bool:
    for collection_key in ("changes", "updatedFrom", "updated_from"):
        if _status_from_change_collection(_get_value(context, (collection_key,))) is not None:
            return True

    for fields_key in ("updatedFields", "changedFields"):
        if _mentions_status_field(_get_value(context, (fields_key,))):
            return True

    return False


def _status_from_change_collection(changes: Any) -> str | None:
    if not isinstance(changes, Mapping):
        return None

    for key in STATUS_FIELDS:
        if key not in changes:
            continue

        change = changes[key]
        if isinstance(change, Mapping):
            status = _value_name(_first_direct_value(change, CHANGE_TO_FIELDS))
            if status:
                return status

        status = _value_name(change)
        if status:
            return status

    return None


def _mentions_status_field(fields: Any) -> bool:
    if isinstance(fields, str):
        return _normalize(fields) in {_normalize(field) for field in STATUS_FIELDS}

    if isinstance(fields, Iterable):
        return any(_mentions_status_field(field) for field in fields)

    return False


def _status_from_issue(context: Mapping[str, Any]) -> str | None:
    issue = _get_value(context, ("issue",))
    if not isinstance(issue, Mapping):
        return None

    return _value_name(_first_direct_value(issue, STATUS_FIELDS))


def _value_name(value: Any) -> str | None:
    if isinstance(value, Mapping):
        value = _first_direct_value(value, ("name", "title", "label"))

    if value is None:
        return None

    text = str(value).strip()
    return text or None


def _get_value(context: Mapping[str, Any], keys: Iterable[str]) -> Any:
    current: Any = context
    for key in keys:
        if not isinstance(current, Mapping) or key not in current:
            return None
        current = current[key]
    return current


def _first_direct_value(context: Mapping[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        if key in context:
            return context[key]
    return None


def _direct_values(context: Mapping[str, Any], keys: Iterable[str]) -> Iterable[Any]:
    for key in keys:
        if key in context:
            yield context[key]


def _normalize(value: Any) -> str | None:
    if value is None:
        return None

    camel_spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", str(value))
    words = re.sub(r"[_-]+", " ", camel_spaced).strip().lower()
    return re.sub(r"\s+", " ", words)


def _has_prefix(title: str) -> bool:
    prefix = _normalize(PREFIX)
    normalized_title = _normalize(title)
    return bool(prefix and normalized_title and normalized_title.startswith(prefix))


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
