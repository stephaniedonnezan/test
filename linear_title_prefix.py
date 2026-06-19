"""Build Linear issue title updates for research status changes.

The module is dependency-free so it can be used as a small JSON-in/JSON-out
step by automation runners that receive Linear issue webhook payloads.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_CHANGE_TRIGGERS = {
    "status changed",
    "status change",
    "status update",
    "status updated",
}
ISSUE_UPDATE_TRIGGERS = {
    "issue update",
    "issue updated",
    "updated issue",
    "update",
}
STATUS_FIELDS = ("status", "state", "workflowState")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title-update action when an issue enters research."""

    if not isinstance(event, Mapping) or not _is_status_change_event(event):
        return None

    status = _new_status(event)
    if _normalize(status) != TARGET_STATUS:
        return None

    issue_id = _clean_string(_first_value(event, ("id", "issueId", "issue_id", "identifier", "key")))
    title = _clean_string(_first_value(event, ("title", "name")))
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
                    ("trigger", "type", "webhookType", "action"),
                )
            )
            if normalized
        }
        if triggers & STATUS_CHANGE_TRIGGERS:
            return True

        if triggers & ISSUE_UPDATE_TRIGGERS and _status_changed(context):
            return True

        if _status_changed(context) and _new_status_from_context(context):
            return True

    return False


def _new_status(event: Mapping[str, Any]) -> str | None:
    for context in _candidate_contexts(event):
        status = _new_status_from_context(context)
        if status:
            return status
    return None


def _new_status_from_context(context: Mapping[str, Any]) -> str | None:
    status = _first_direct_value(
        context,
        ("newStatus", "new_status", "status", "state", "workflowState"),
    )
    status = _status_name(status)
    if status:
        return status

    changes = _get_value(context, ("changes",))
    if isinstance(changes, Mapping):
        for key in STATUS_FIELDS:
            status = _changed_to_value(changes.get(key))
            if status:
                return status

    updated_from = _get_value(context, ("updatedFrom",))
    if isinstance(updated_from, Mapping):
        for key in STATUS_FIELDS:
            if key in updated_from:
                current_status = _first_direct_value(context, (key,))
                status = _status_name(current_status)
                if status:
                    return status

    issue = _get_value(context, ("issue",))
    if isinstance(issue, Mapping):
        for key in STATUS_FIELDS:
            status = _status_name(issue.get(key))
            if status:
                return status

    return None


def _changed_to_value(change: Any) -> str | None:
    if isinstance(change, Mapping):
        changed_to = _first_direct_value(
            change,
            ("newValue", "new_value", "to", "toValue", "to_value", "after"),
        )
        return _status_name(changed_to)

    return _status_name(change)


def _status_name(status: Any) -> str | None:
    if isinstance(status, Mapping):
        value = _first_direct_value(status, ("name", "title", "label"))
        if value is not None:
            return _clean_string(value)
        return None

    return _clean_string(status)


def _first_value(event: Mapping[str, Any], keys: Iterable[str]) -> Any:
    for context in _candidate_contexts(event):
        value = _first_direct_value(context, keys)
        if _clean_string(value):
            return value
    return None


def _candidate_contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    yield event

    for path in (
        ("automation_trigger_info",),
        ("automation_trigger_info", "triggerContext"),
        ("triggerContext",),
        ("trigger_context",),
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
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        fields = _get_value(context, (key,))
        if _field_list_mentions_status(fields):
            return True

    changes = _get_value(context, ("changes",))
    if isinstance(changes, Mapping):
        for key in STATUS_FIELDS:
            if key in changes:
                return True

    updated_from = _get_value(context, ("updatedFrom",))
    if isinstance(updated_from, Mapping):
        for key in STATUS_FIELDS:
            if key in updated_from:
                return True

    return False


def _field_list_mentions_status(fields: Any) -> bool:
    if isinstance(fields, str):
        field_values = (fields,)
    elif isinstance(fields, Iterable):
        field_values = fields
    else:
        return False

    return any(_normalize(field) in {_normalize(key) for key in STATUS_FIELDS} for field in field_values)


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


def _clean_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize(value: Any) -> str | None:
    if value is None:
        return None
    camel_spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", str(value))
    words = re.sub(r"[_-]+", " ", camel_spaced).strip().lower()
    return re.sub(r"\s+", " ", words)


def _has_prefix(title: str) -> bool:
    normalized_title = _normalize(title) or ""
    normalized_prefix = _normalize(PREFIX) or ""
    return normalized_title.startswith(normalized_prefix)


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
