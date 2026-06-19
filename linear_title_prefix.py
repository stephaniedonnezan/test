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
STATUS_FIELDS = ("status", "state", "workflowState", "workflow_status")
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

    issue_id = _first_value(event, ("issueId", "issue_id", "id", "identifier", "key"))
    title = _first_value(event, ("title", "name"))
    if not issue_id or not title or _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title.strip()}",
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
                "newWorkflowState",
                "new_workflow_state",
            ),
        )
        status_name = _status_name(status)
        if status_name:
            return status_name

        changes = _get_value(context, ("changes",))
        if isinstance(changes, Mapping):
            for key in STATUS_FIELDS:
                change = changes.get(key)
                changed_to = _changed_to_value(change)
                if changed_to:
                    return changed_to

        status = _first_direct_value(context, STATUS_FIELDS)
        status_name = _status_name(status)
        if status_name:
            return status_name

        issue_status = _first_direct_value(
            _mapping_value(context, "issue"),
            STATUS_FIELDS,
        )
        status_name = _status_name(issue_status)
        if status_name:
            return status_name

    return None


def _first_value(event: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for context in _candidate_contexts(event):
        value = _first_direct_value(context, keys)
        if value is not None:
            stripped = str(value).strip()
            if stripped:
                return stripped
    return None


def _candidate_contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely Linear/Cursor payload locations from broad to narrow."""

    yield event

    for path in (
        ("automation_trigger_info",),
        ("automation_trigger_info", "triggerContext"),
        ("automationTriggerInfo",),
        ("automationTriggerInfo", "triggerContext"),
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
    if isinstance(updated_fields, Iterable) and not isinstance(
        updated_fields,
        (str, bytes, Mapping),
    ):
        normalized_status_fields = {
            _normalize(status_field) for status_field in STATUS_FIELDS
        }
        return any(_normalize(field) in normalized_status_fields for field in updated_fields)

    return False


def _changed_to_value(change: Any) -> str | None:
    if isinstance(change, Mapping):
        for key in ("newValue", "new_value", "to", "toValue", "to_value", "after"):
            status_name = _status_name(change.get(key))
            if status_name:
                return status_name

        status_name = _status_name(change)
        if status_name:
            return status_name
    elif change is not None:
        return str(change)

    return None


def _status_name(value: Any) -> str | None:
    if isinstance(value, Mapping):
        return _first_value(value, ("name", "title", "label"))
    if value is not None:
        stripped = str(value).strip()
        if stripped:
            return stripped
    return None


def _mapping_value(context: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = context.get(key)
    if isinstance(value, Mapping):
        return value
    return {}


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
    return bool(normalized_prefix and normalized_title and normalized_title.startswith(normalized_prefix))


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
