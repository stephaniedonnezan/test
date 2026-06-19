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
STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow state"}
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

    issue_id = _first_value(event, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_value(event, ("title", "name"))
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
                "status",
                "state",
                "workflowState",
            ),
        )
        status_name = _status_name(status)
        if status_name:
            return status_name

        changed_to = _changed_to_status(context)
        if changed_to:
            return changed_to

        issue_status = _issue_status(context)
        if issue_status:
            return issue_status

    return None


def _first_value(event: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for context in _candidate_contexts(event):
        value = _first_direct_value(context, keys)
        if value is not None:
            text = str(value).strip()
            if text:
                return text
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
    if isinstance(changes, Mapping):
        for key in changes:
            if _is_status_field(key):
                return True

    updated_from = _get_value(context, ("updatedFrom",))
    if isinstance(updated_from, Mapping):
        for key in updated_from:
            if _is_status_field(key):
                return True

    updated_fields = _get_value(context, ("updatedFields",))
    if isinstance(updated_fields, Iterable) and not isinstance(updated_fields, (str, bytes)):
        return any(_is_status_field(field) for field in updated_fields)

    return False


def _changed_to_status(context: Mapping[str, Any]) -> str | None:
    changes = _get_value(context, ("changes",))
    if not isinstance(changes, Mapping):
        return None

    for key, change in changes.items():
        if not _is_status_field(key):
            continue

        if isinstance(change, Mapping):
            changed_to = _first_direct_value(
                change,
                ("newValue", "to", "toValue", "after", "new"),
            )
            status_name = _status_name(changed_to)
            if status_name:
                return status_name
        elif change:
            return str(change).strip()

    return None


def _issue_status(context: Mapping[str, Any]) -> str | None:
    for path in (
        ("issue", "status"),
        ("issue", "state"),
        ("issue", "workflowState"),
    ):
        status_name = _status_name(_get_value(context, path))
        if status_name:
            return status_name

    return None


def _status_name(value: Any) -> str | None:
    if isinstance(value, Mapping):
        value = _first_direct_value(value, ("name", "title", "label"))
    if value is None:
        return None

    text = str(value).strip()
    return text or None


def _is_status_field(value: Any) -> bool:
    normalized = _normalize(value)
    return normalized in STATUS_FIELD_NAMES


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
