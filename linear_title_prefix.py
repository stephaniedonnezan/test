"""Build Linear issue title updates for research status changes.

The module is intentionally dependency-free so it can be used as a small
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
STATUS_CHANGE_FIELDS = ("status", "state", "workflowState", "workflow_state")
STATUS_CHANGE_TRIGGERS = {
    "status changed",
    "status change",
    "status update",
    "status updated",
}
GENERIC_UPDATE_TRIGGERS = {
    "issue updated",
    "updated issue",
    "update",
    "updated",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title-update action when an issue enters research."""

    if not isinstance(event, Mapping) or not _is_status_change_event(event):
        return None

    status = _new_status(event)
    if _normalize(status) != TARGET_STATUS:
        return None

    issue_id = _issue_id(event)
    title = _first_value(event, ("title", "name"))
    if not issue_id or not title:
        return None

    issue_id = str(issue_id).strip()
    title = str(title).strip()
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
            for value in _direct_values(context, ("trigger", "type", "webhookType", "action"))
            if (normalized := _normalize(value))
        }

        if triggers & STATUS_CHANGE_TRIGGERS:
            return True

        if triggers & GENERIC_UPDATE_TRIGGERS and _status_changed(context):
            return True

        if _status_changed(context) and _new_status(context):
            return True

    return False


def _new_status(event: Mapping[str, Any]) -> str | None:
    for context in _candidate_contexts(event):
        status = _first_direct_value(
            context,
            (
                "newStatus",
                "new_status",
                "statusName",
                "status_name",
                "stateName",
                "state_name",
                "workflowStateName",
                "workflow_state_name",
            ),
        )
        status = _name_from_value(status)
        if status:
            return status

        changes = _get_value(context, ("changes",))
        changed_status = _changed_status_from_mapping(changes)
        if changed_status:
            return changed_status

        updated_from_status = _current_status_when_updated_from(context)
        if updated_from_status:
            return updated_from_status

        status = _first_direct_value(
            context,
            ("status", "state", "workflowState", "workflow_state"),
        )
        status = _name_from_value(status)
        if status:
            return status

        issue_status = _current_issue_status(context)
        if issue_status:
            return issue_status

    return None


def _first_value(event: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for context in _candidate_contexts(event):
        value = _first_direct_value(context, keys)
        if value:
            return str(value)
    return None


def _issue_id(event: Mapping[str, Any]) -> str | None:
    issue_id = _first_value(event, ("issueId", "issue_id", "identifier", "key"))
    if issue_id:
        return issue_id

    for context in _candidate_contexts(event):
        if context is event and (
            isinstance(_get_value(event, ("data", "issue")), Mapping)
            or isinstance(_get_value(event, ("issue",)), Mapping)
            or isinstance(_get_value(event, ("payload", "issue")), Mapping)
        ):
            continue

        value = _first_direct_value(context, ("id",))
        if value:
            return str(value)

    return None


def _candidate_contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    yield event

    for path in (
        ("triggerContext",),
        ("data",),
        ("data", "issue"),
        ("issue",),
        ("payload",),
        ("payload", "issue"),
    ):
        value = _get_value(event, path)
        if isinstance(value, Mapping):
            yield value


def _status_changed(context: Mapping[str, Any]) -> bool:
    changes = _get_value(context, ("changes",))
    if isinstance(changes, Mapping) and any(key in changes for key in STATUS_CHANGE_FIELDS):
        return True

    updated_from = _get_value(context, ("updatedFrom",))
    if isinstance(updated_from, Mapping) and any(
        key in updated_from for key in STATUS_CHANGE_FIELDS
    ):
        return True

    updated_fields = _get_value(context, ("updatedFields",))
    if isinstance(updated_fields, Iterable) and not isinstance(updated_fields, (str, bytes)):
        normalized_fields = {_normalize(field) for field in updated_fields}
        return bool(normalized_fields & {_normalize(field) for field in STATUS_CHANGE_FIELDS})

    return False


def _changed_status_from_mapping(changes: Any) -> str | None:
    if not isinstance(changes, Mapping):
        return None

    for key in STATUS_CHANGE_FIELDS:
        change = changes.get(key)
        if not change:
            continue

        if isinstance(change, Mapping):
            changed_to = _first_direct_value(
                change,
                ("newValue", "new_value", "to", "toValue", "to_value", "after"),
            )
            status = _name_from_value(changed_to)
            if status:
                return status
        else:
            return str(change)

    return None


def _current_status_when_updated_from(context: Mapping[str, Any]) -> str | None:
    updated_from = _get_value(context, ("updatedFrom",))
    if not isinstance(updated_from, Mapping):
        return None

    return _current_issue_status(context) or _name_from_value(
        _first_direct_value(context, ("status", "state", "workflowState", "workflow_state"))
    )


def _current_issue_status(context: Mapping[str, Any]) -> str | None:
    issue = _get_value(context, ("issue",))
    if isinstance(issue, Mapping):
        status = _first_direct_value(
            issue,
            ("status", "state", "workflowState", "workflow_state"),
        )
        return _name_from_value(status)
    return None


def _name_from_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        value = _first_direct_value(value, ("name", "title", "label"))
    if value:
        return str(value)
    return None


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
    normalized_prefix = _normalize(PREFIX)
    normalized_title = _normalize(title)
    return bool(normalized_prefix and normalized_title.startswith(normalized_prefix))


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
