"""Build Linear issue-title updates for research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow state", "workflow status"}
_DIRECT_STATUS_TRIGGERS = {"statuschanged", "status change", "status changed"}
_GENERIC_UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return an issue-title update action for Linear research status changes.

    The automation runner supplies a flat ``triggerContext`` payload, while
    Linear webhooks are commonly nested under ``data.issue``. This function
    accepts both shapes and returns ``None`` when no title update is needed.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_change_event(contexts):
        return None

    new_status = _extract_new_status(contexts)
    if _normalize_text(new_status) != TARGET_STATUS:
        return None

    issue_id = _first_text(contexts, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_text(contexts, ("title", "name"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []

    trigger_context = _mapping_at(event, "triggerContext")
    if trigger_context:
        contexts.append(trigger_context)

    data = _mapping_at(event, "data")
    issue = _mapping_at(data, "issue") if data else None
    if issue:
        contexts.append(issue)
    if data:
        contexts.append(data)

    contexts.append(event)
    return contexts


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    trigger_values = []
    for context in contexts:
        for key in ("trigger", "webhookType", "action", "type"):
            value = context.get(key)
            if _is_text(value):
                trigger_values.append(_normalize_text(value))

    if any(value in _DIRECT_STATUS_TRIGGERS for value in trigger_values):
        return True

    if any(value in _GENERIC_UPDATE_TRIGGERS for value in trigger_values):
        return _updated_fields_include_status(contexts)

    return False


def _updated_fields_include_status(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            fields = context.get(key)
            if _field_collection_has_status(fields):
                return True

        changes = context.get("changes")
        if isinstance(changes, Mapping):
            for field in changes:
                if _is_status_field(field):
                    return True
        elif isinstance(changes, list):
            for change in changes:
                if isinstance(change, Mapping):
                    field = change.get("field") or change.get("name") or change.get("key")
                    if _is_status_field(field):
                        return True
                elif _is_status_field(change):
                    return True

    return False


def _field_collection_has_status(fields: Any) -> bool:
    if isinstance(fields, str):
        return _is_status_field(fields)

    if isinstance(fields, list | tuple | set):
        return any(_is_status_field(field) for field in fields)

    if isinstance(fields, Mapping):
        return any(_is_status_field(field) for field in fields)

    return False


def _extract_new_status(contexts: list[Mapping[str, Any]]) -> str | None:
    for key in ("newStatus", "new_status", "toStatus", "to_status"):
        status = _first_status_value(contexts, key)
        if status:
            return status

    status_from_changes = _status_from_changes(contexts)
    if status_from_changes:
        return status_from_changes

    for key in ("status", "state", "workflowState", "workflow_state"):
        status = _first_status_value(contexts, key)
        if status:
            return status

    return None


def _status_from_changes(contexts: list[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        changes = context.get("changes")
        if isinstance(changes, Mapping):
            for field, change in changes.items():
                if not _is_status_field(field):
                    continue
                value = _new_value_from_change(change)
                if value:
                    return value
        elif isinstance(changes, list):
            for change in changes:
                if not isinstance(change, Mapping):
                    continue
                field = change.get("field") or change.get("name") or change.get("key")
                if not _is_status_field(field):
                    continue
                value = _new_value_from_change(change)
                if value:
                    return value

    return None


def _new_value_from_change(change: Any) -> str | None:
    if isinstance(change, Mapping):
        for key in ("newValue", "new_value", "to", "after", "value"):
            value = _coerce_status_value(change.get(key))
            if value:
                return value
    return _coerce_status_value(change)


def _first_status_value(contexts: list[Mapping[str, Any]], key: str) -> str | None:
    for context in contexts:
        value = _coerce_status_value(context.get(key))
        if value:
            return value
    return None


def _coerce_status_value(value: Any) -> str | None:
    if _is_text(value):
        return value.strip()

    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            nested_value = value.get(key)
            if _is_text(nested_value):
                return nested_value.strip()

    return None


def _first_text(contexts: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        for context in contexts:
            value = context.get(key)
            if _is_text(value) and value.strip():
                return value
    return None


def _mapping_at(context: Mapping[str, Any] | None, key: str) -> Mapping[str, Any] | None:
    if not isinstance(context, Mapping):
        return None

    value = context.get(key)
    return value if isinstance(value, Mapping) else None


def _is_status_field(value: Any) -> bool:
    return _normalize_text(value) in _STATUS_FIELD_NAMES


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def _normalize_text(value: Any) -> str:
    if not _is_text(value):
        return ""

    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value.strip())
    spaced = re.sub(r"[_\-/]+", " ", spaced)
    spaced = re.sub(r"[^A-Za-z0-9]+", " ", spaced)
    return re.sub(r"\s+", " ", spaced).strip().lower()


def _is_text(value: Any) -> bool:
    return isinstance(value, str)


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
