"""Build Linear issue title updates for research status transitions.

The automation runner can feed either a flattened Cursor trigger context or a
native Linear webhook payload into this module.  When the event represents an
issue status change to "to research", the handler returns an update action that
prefixes the issue title with "Cursor researching".
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELDS = {"status", "state", "workflowstate", "workflowstatus"}
_STATUS_TRIGGER_VALUES = {
    "status changed",
    "status change",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
}
_ISSUE_UPDATE_VALUES = {
    "issue updated",
    "updated issue",
    "update",
    "updated",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update action when an issue enters To Research.

    The return value is intentionally data-only so the automation layer can
    perform the actual Linear API mutation.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _event_contexts(event)
    if not _is_status_change_event(contexts):
        return None

    new_status = _extract_new_status(contexts)
    if _normalize_words(new_status) != TARGET_STATUS:
        return None

    issue_id = _first_string(contexts, ("issueId", "issue_id", "id", "identifier", "key"))
    title = _first_string(contexts, ("title", "name"))
    if issue_id is None or title is None:
        return None

    title = title.strip()
    if not title or _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _event_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return payload mappings from broadest to most issue-specific."""

    contexts: list[Mapping[str, Any]] = [event]

    for path in (
        ("triggerContext",),
        ("data",),
        ("data", "issue"),
        ("data", "state"),
        ("issue",),
        ("state",),
        ("workflowState",),
        ("webhook",),
        ("payload",),
        ("payload", "issue"),
    ):
        value = _get_path(event, path)
        if isinstance(value, Mapping):
            contexts.append(value)

    return contexts


def _is_status_change_event(contexts: Sequence[Mapping[str, Any]]) -> bool:
    """Detect direct status-change triggers and generic issue-update payloads."""

    for context in contexts:
        for key in ("trigger", "webhookType", "action", "type", "event", "eventType"):
            normalized = _normalize_words(context.get(key))
            if normalized in _STATUS_TRIGGER_VALUES:
                return True

    for context in contexts:
        for key in ("trigger", "webhookType", "action", "type", "event", "eventType"):
            normalized = _normalize_words(context.get(key))
            if normalized in _ISSUE_UPDATE_VALUES and _has_status_field_change(context):
                return True

    return False


def _has_status_field_change(context: Mapping[str, Any]) -> bool:
    updated_fields = context.get("updatedFields")
    if _sequence_contains_status_field(updated_fields):
        return True

    changed_fields = context.get("changedFields")
    if _sequence_contains_status_field(changed_fields):
        return True

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        for key, value in changes.items():
            if _is_status_field_name(key):
                return True
            if isinstance(value, Mapping) and _is_status_field_name(
                value.get("field") or value.get("name") or value.get("key")
            ):
                return True
    elif isinstance(changes, Sequence) and not isinstance(changes, (str, bytes)):
        for change in changes:
            if isinstance(change, Mapping) and _is_status_field_name(
                change.get("field") or change.get("name") or change.get("key")
            ):
                return True

    return False


def _extract_new_status(contexts: Sequence[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        status = _first_string(
            (context,),
            (
                "newStatus",
                "new_status",
                "toStatus",
                "to_status",
                "statusName",
                "status_name",
                "stateName",
                "state_name",
                "workflowStateName",
                "workflow_state_name",
            ),
        )
        if status:
            return status

    for context in contexts:
        status = _status_from_changes(context.get("changes"))
        if status:
            return status

    for context in contexts:
        for key in ("status", "state", "workflowState", "workflowStatus"):
            status = _status_value(context.get(key))
            if status:
                return status

    return None


def _status_from_changes(changes: Any) -> str | None:
    if isinstance(changes, Mapping):
        for key, value in changes.items():
            if not _is_status_field_name(key):
                continue
            status = _change_to_value(value)
            if status:
                return status

        for value in changes.values():
            if not isinstance(value, Mapping):
                continue
            if not _is_status_field_name(value.get("field") or value.get("name") or value.get("key")):
                continue
            status = _change_to_value(value)
            if status:
                return status

    if isinstance(changes, Sequence) and not isinstance(changes, (str, bytes)):
        for change in changes:
            if not isinstance(change, Mapping):
                continue
            if not _is_status_field_name(change.get("field") or change.get("name") or change.get("key")):
                continue
            status = _change_to_value(change)
            if status:
                return status

    return None


def _change_to_value(change: Any) -> str | None:
    if isinstance(change, Mapping):
        for key in ("to", "new", "newValue", "value", "after"):
            status = _status_value(change.get(key))
            if status:
                return status
    return _status_value(change)


def _status_value(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, Mapping):
        for key in ("name", "title", "label", "status", "state"):
            status = _status_value(value.get(key))
            if status:
                return status
    return None


def _first_string(contexts: Sequence[Mapping[str, Any]], keys: Sequence[str]) -> str | None:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _get_path(mapping: Mapping[str, Any], path: Sequence[str]) -> Any:
    value: Any = mapping
    for key in path:
        if not isinstance(value, Mapping):
            return None
        value = value.get(key)
    return value


def _sequence_contains_status_field(value: Any) -> bool:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return any(_is_status_field_name(item) for item in value)
    return False


def _is_status_field_name(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    normalized = re.sub(r"[^a-z0-9]+", "", _split_camel_case(value).lower())
    return normalized in _STATUS_FIELDS


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def _normalize_words(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    value = _split_camel_case(value)
    value = re.sub(r"[^A-Za-z0-9]+", " ", value)
    return " ".join(value.lower().split())


def _split_camel_case(value: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)


def main() -> int:
    event = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(event), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
