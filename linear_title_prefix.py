"""Build Linear issue title updates for Cursor research automation.

The module is intentionally dependency-free so it can run in small automation
repositories. It reads common Cursor/Linear webhook payload shapes and emits a
single JSON-serializable update action when an issue moves to "To Research".
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"

_STATUS_FIELDS = {"status", "state", "workflowstate", "workflow state"}
_STATUS_CHANGED_EVENTS = {
    "status changed",
    "status change",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
}
_GENERIC_UPDATE_EVENTS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to To Research."""
    if not isinstance(event, Mapping):
        return None

    contexts = list(_candidate_contexts(event))
    if not _is_status_change_event(contexts):
        return None

    status = _extract_new_status(contexts)
    if _normalize_text(status) != TARGET_STATUS:
        return None

    issue_id = _first_text(contexts, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_text(contexts, ("title", "name"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if not title or title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _candidate_contexts(event: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    """Return useful payload layers from outermost metadata to nested issue data."""
    contexts: list[Mapping[str, Any]] = []

    trigger_context = _mapping_at(event, "triggerContext")
    if trigger_context:
        contexts.append(trigger_context)

    data = _mapping_at(event, "data")
    if data:
        data_issue = _mapping_at(data, "issue")
        if data_issue:
            contexts.append(data_issue)

    issue = _mapping_at(event, "issue")
    if issue:
        contexts.append(issue)

    if data:
        contexts.append(data)

    contexts.append(event)

    # De-duplicate objects while preserving precedence.
    seen: set[int] = set()
    unique_contexts: list[Mapping[str, Any]] = []
    for context in contexts:
        context_id = id(context)
        if context_id not in seen:
            seen.add(context_id)
            unique_contexts.append(context)
    return tuple(unique_contexts)


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    event_names = {
        _normalize_text(context.get(key))
        for context in contexts
        for key in ("trigger", "webhookType", "action", "type")
    }
    event_names.discard("")

    if event_names & _STATUS_CHANGED_EVENTS:
        return True

    if event_names & _GENERIC_UPDATE_EVENTS:
        return _status_field_changed(contexts)

    return False


def _status_field_changed(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            fields = context.get(key)
            if _contains_status_field(fields):
                return True

        for key in ("changes", "changedProperties", "changed_properties"):
            changes = context.get(key)
            if isinstance(changes, Mapping):
                if any(_is_status_field(field) for field in changes):
                    return True
            elif _contains_status_field(changes):
                return True

    return False


def _extract_new_status(contexts: list[Mapping[str, Any]]) -> str | None:
    explicit_keys = (
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
    )
    explicit = _first_text(contexts, explicit_keys)
    if explicit:
        return explicit

    changed = _status_from_change_metadata(contexts)
    if changed:
        return changed

    return _first_text(contexts, ("status", "state", "workflowState", "workflow_state"))


def _status_from_change_metadata(contexts: list[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        updated_fields = context.get("updatedFields") or context.get("updated_fields")
        if isinstance(updated_fields, Mapping):
            value = _value_for_status_key(updated_fields)
            if value:
                return _change_value_to_text(value)

        changes = (
            context.get("changes")
            or context.get("changedProperties")
            or context.get("changed_properties")
        )
        if isinstance(changes, Mapping):
            value = _value_for_status_key(changes)
            if value:
                return _change_value_to_text(value)

    return None


def _change_value_to_text(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("to", "new", "newValue", "new_value", "after", "name", "title"):
            text = _text(value.get(key))
            if text:
                return text
    return _text(value)


def _value_for_status_key(mapping: Mapping[str, Any]) -> Any:
    for key, value in mapping.items():
        if _is_status_field(key):
            return value
    return None


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(_is_status_field(field) for field in value)
    if isinstance(value, (list, tuple, set)):
        return any(_contains_status_field(item) for item in value)
    return _is_status_field(value)


def _is_status_field(value: Any) -> bool:
    return _normalize_text(value) in _STATUS_FIELDS


def _first_text(contexts: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for context in contexts:
        for key in keys:
            text = _text(context.get(key))
            if text:
                return text
    return None


def _mapping_at(mapping: Mapping[str, Any], key: str) -> Mapping[str, Any] | None:
    value = mapping.get(key)
    return value if isinstance(value, Mapping) else None


def _text(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        for key in ("name", "title", "id", "identifier"):
            text = _text(value.get(key))
            if text:
                return text
    return None


def _normalize_text(value: Any) -> str:
    text = _text(value)
    if not text:
        return ""
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.casefold().split())


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 2

    update = build_issue_title_update(event)
    if update is None:
        return 1

    print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
