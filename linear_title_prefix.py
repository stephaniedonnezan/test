"""Build Linear issue title updates for research-status automation.

The automation receives Linear webhook payloads in a few shapes.  This module
keeps the decision small and deterministic: when an issue status changes to
"to research", return the title update action that adds the Cursor research
prefix.  All other payloads are ignored.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


ACTION = "update_issue_title"
PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow state"}
_TRIGGER_KEYS = {
    "trigger",
    "webhookType",
    "webhook_type",
    "action",
    "type",
    "event",
    "eventType",
    "event_type",
}
_NEW_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "toStatus",
    "to_status",
    "status",
    "statusName",
    "status_name",
    "state",
    "workflowState",
    "workflow_state",
)
_ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "key", "id")
_TITLE_KEYS = ("title", "name", "summary")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return the Linear title update action for a matching status-change event."""

    if not isinstance(event, Mapping):
        return None

    contexts = list(_contexts(event))
    if not _is_status_change_event(contexts):
        return None

    new_status = _extract_new_status(contexts)
    if _normalize_words(new_status) != TARGET_STATUS:
        return None

    issue_id = _extract_first_string(contexts, _ISSUE_ID_KEYS)
    title = _extract_first_string(contexts, _TITLE_KEYS)
    if not issue_id or not title:
        return None

    title = title.strip()
    if not title or _has_prefix(title):
        return None

    return {
        "action": ACTION,
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield useful payload scopes from most-specific to least-specific fields."""

    trigger_context = _mapping_at(event, "triggerContext")
    data = _mapping_at(event, "data")
    issue = _mapping_at(event, "issue")
    data_issue = _mapping_at(data, "issue") if data else None

    for context in (trigger_context, data_issue, issue, data, event):
        if context:
            yield context


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    trigger_values = [
        value
        for context in contexts
        for key, value in context.items()
        if key in _TRIGGER_KEYS and isinstance(value, str)
    ]
    normalized_triggers = {_normalize_words(value) for value in trigger_values}

    if "status changed" in normalized_triggers or "status change" in normalized_triggers:
        return True

    issue_update_triggers = {"issue updated", "updated issue", "update", "updated"}
    if normalized_triggers.intersection(issue_update_triggers):
        return _has_status_update_field(contexts)

    return False


def _has_status_update_field(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        if _field_list_mentions_status(context.get("updatedFields")):
            return True
        if _field_list_mentions_status(context.get("changedFields")):
            return True
        if _changes_mentions_status(context.get("changes")):
            return True
        if _changes_mentions_status(context.get("updatedProperties")):
            return True
    return False


def _field_list_mentions_status(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_words(value) in _STATUS_FIELD_NAMES
    if isinstance(value, Iterable) and not isinstance(value, (bytes, str, Mapping)):
        return any(_field_list_mentions_status(item) for item in value)
    return False


def _changes_mentions_status(value: Any) -> bool:
    if not isinstance(value, Mapping):
        return False
    return any(_normalize_words(str(key)) in _STATUS_FIELD_NAMES for key in value)


def _extract_new_status(contexts: list[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        for key in ("newStatus", "new_status", "toStatus", "to_status"):
            status = _string_or_name(context.get(key))
            if status:
                return status

    for context in contexts:
        status = _status_from_changes(context.get("changes"))
        if status:
            return status
        status = _status_from_changes(context.get("updatedProperties"))
        if status:
            return status

    for context in contexts:
        for key in _NEW_STATUS_KEYS:
            status = _string_or_name(context.get(key))
            if status:
                return status

    return None


def _status_from_changes(value: Any) -> str | None:
    if not isinstance(value, Mapping):
        return None

    for key, change in value.items():
        if _normalize_words(str(key)) not in _STATUS_FIELD_NAMES:
            continue
        if isinstance(change, Mapping):
            for nested_key in ("to", "new", "newValue", "after"):
                status = _string_or_name(change.get(nested_key))
                if status:
                    return status
        status = _string_or_name(change)
        if status:
            return status
    return None


def _string_or_name(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, Mapping):
        for key in ("name", "title", "value"):
            nested = value.get(key)
            if isinstance(nested, str) and nested.strip():
                return nested.strip()
    return None


def _extract_first_string(
    contexts: list[Mapping[str, Any]], keys: tuple[str, ...]
) -> str | None:
    for key in keys:
        for context in contexts:
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _mapping_at(mapping: Mapping[str, Any] | None, key: str) -> Mapping[str, Any] | None:
    if not isinstance(mapping, Mapping):
        return None
    value = mapping.get(key)
    return value if isinstance(value, Mapping) else None


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def _normalize_words(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    value = re.sub(r"[^A-Za-z0-9]+", " ", value)
    return " ".join(value.casefold().split())


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    print(json.dumps(action, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
