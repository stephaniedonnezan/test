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
STATUS_FIELDS = ("status", "state", "workflowState", "workflow_state")
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
    title = _issue_title(event)
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
            _normalize(value)
            for value in _direct_values(
                context,
                ("trigger", "type", "webhookType", "webhook_type", "action"),
            )
        }
        if triggers & STATUS_CHANGE_TRIGGERS:
            return True

        if triggers & GENERIC_UPDATE_TRIGGERS and _status_changed(context):
            return True

        if _status_changed(context):
            return True

    return False


def _new_status(event: Mapping[str, Any]) -> str | None:
    for context in _candidate_contexts(event):
        status = _first_direct_value(
            context,
            (
                "newStatus",
                "new_status",
                "newState",
                "new_state",
                "status",
                "state",
                "workflowState",
                "workflow_state",
            ),
        )
        status_name = _status_name(status)
        if status_name:
            return status_name

        changed_to = _changed_to_status(context)
        if changed_to:
            return changed_to

        issue_state = _get_value(context, ("issue", "state"))
        state_name = _status_name(issue_state)
        if state_name:
            return state_name

        issue_workflow_state = _get_value(context, ("issue", "workflowState"))
        workflow_state_name = _status_name(issue_workflow_state)
        if workflow_state_name:
            return workflow_state_name

    return None


def _issue_id(event: Mapping[str, Any]) -> str | None:
    return _first_value(
        event,
        (
            "issueId",
            "issue_id",
            "identifier",
            "key",
            "id",
        ),
    )


def _issue_title(event: Mapping[str, Any]) -> str | None:
    title = _first_value(event, ("title", "name"))
    if title is None:
        return None

    stripped = title.strip()
    return stripped or None


def _first_value(event: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for context in _issue_contexts(event):
        value = _first_direct_value(context, keys)
        if value:
            return str(value).strip()
    return None


def _issue_contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield issue-shaped contexts before outer webhook metadata."""

    for path in (
        ("triggerContext",),
        ("data", "issue"),
        ("issue",),
        ("payload", "issue"),
        ("data",),
        ("payload",),
    ):
        value = _get_value(event, path)
        if isinstance(value, Mapping):
            yield value

    yield event


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
    if isinstance(changes, Mapping) and any(key in changes for key in STATUS_FIELDS):
        return True

    updated_from = _get_value(context, ("updatedFrom",))
    if isinstance(updated_from, Mapping) and any(
        key in updated_from for key in STATUS_FIELDS
    ):
        return True

    updated_fields = _get_value(context, ("updatedFields",))
    if isinstance(updated_fields, str):
        return _normalize(updated_fields) in {_normalize(field) for field in STATUS_FIELDS}
    if isinstance(updated_fields, Iterable):
        return any(
            _normalize(field) in {_normalize(status_field) for status_field in STATUS_FIELDS}
            for field in updated_fields
        )

    return False


def _changed_to_status(context: Mapping[str, Any]) -> str | None:
    changes = _get_value(context, ("changes",))
    if not isinstance(changes, Mapping):
        return None

    for key in STATUS_FIELDS:
        change = changes.get(key)
        if isinstance(change, Mapping):
            changed_to = _first_direct_value(
                change,
                ("newValue", "new_value", "to", "toValue", "to_value", "after"),
            )
            status_name = _status_name(changed_to)
            if status_name:
                return status_name
        else:
            status_name = _status_name(change)
            if status_name:
                return status_name

    return None


def _status_name(value: Any) -> str | None:
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
    return bool(_normalize(title).startswith(_normalize(PREFIX)))


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
