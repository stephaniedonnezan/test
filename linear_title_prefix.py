"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow state"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when an issue moves to "to research"."""
    if not isinstance(event, Mapping):
        return None

    contexts = _collect_contexts(event)
    if not _is_status_change_event(contexts):
        return None

    status = _new_status(contexts)
    if _normalize(status) != TARGET_STATUS:
        return None

    title = _string_value(_first_value(contexts, ("title", "name")))
    issue_id = _string_value(
        _first_value(contexts, ("issueId", "issue_id", "identifier", "key", "id"))
    )
    if not title or not issue_id:
        return None

    if _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _collect_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Collect likely metadata and issue objects in precedence order."""
    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)

    add(event.get("triggerContext"))
    add(event)
    add(event.get("data"))
    add(event.get("issue"))

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        add(trigger_context.get("data"))
        add(trigger_context.get("issue"))

    data = event.get("data")
    if isinstance(data, Mapping):
        add(data.get("issue"))
        add(data.get("state"))
        add(data.get("workflowState"))

    issue = data.get("issue") if isinstance(data, Mapping) else event.get("issue")
    if isinstance(issue, Mapping):
        add(issue.get("state"))
        add(issue.get("workflowState"))

    return contexts


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    event_names = (
        "trigger",
        "webhookType",
        "webhook_type",
        "action",
        "type",
        "event",
        "eventType",
        "event_type",
    )
    for value in _values_for_keys(contexts, event_names):
        normalized = _normalize(value)
        if normalized in {
            "status changed",
            "status change",
            "state changed",
            "workflow state changed",
        }:
            return True

    if any(_normalize(value) in {"update", "updated", "issue updated", "updated issue"} for value in _values_for_keys(contexts, event_names)):
        return _updated_fields_include_status(contexts) or _changes_include_status(contexts)

    return False


def _updated_fields_include_status(contexts: list[Mapping[str, Any]]) -> bool:
    for value in _values_for_keys(contexts, ("updatedFields", "updated_fields", "changedFields", "changed_fields")):
        if isinstance(value, str):
            fields = [value]
        elif isinstance(value, list | tuple | set):
            fields = value
        else:
            continue

        for field in fields:
            if _normalize(field) in STATUS_FIELD_NAMES:
                return True
    return False


def _changes_include_status(contexts: list[Mapping[str, Any]]) -> bool:
    for changes in _values_for_keys(contexts, ("changes", "changed")):
        if not isinstance(changes, Mapping):
            continue
        for field in changes:
            if _normalize(field) in STATUS_FIELD_NAMES:
                return True
    return False


def _new_status(contexts: list[Mapping[str, Any]]) -> str | None:
    explicit_status = _first_value(
        contexts,
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
    if explicit_status is not None:
        return _string_value(explicit_status)

    for changes in _values_for_keys(contexts, ("changes", "changed")):
        changed_status = _status_from_changes(changes)
        if changed_status:
            return changed_status

    status = _first_value(contexts, ("status", "state", "workflowState", "workflow_state"))
    return _string_value(status)


def _status_from_changes(changes: Any) -> str | None:
    if not isinstance(changes, Mapping):
        return None

    for field, value in changes.items():
        if _normalize(field) not in STATUS_FIELD_NAMES:
            continue
        if isinstance(value, Mapping):
            candidate = _first_mapping_value(value, ("to", "new", "after", "value", "name"))
            return _string_value(candidate)
        return _string_value(value)
    return None


def _first_value(contexts: list[Mapping[str, Any]], keys: tuple[str, ...]) -> Any:
    for context in contexts:
        value = _first_mapping_value(context, keys)
        if value is not None:
            return value
    return None


def _first_mapping_value(mapping: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key not in mapping:
            continue
        value = mapping[key]
        if isinstance(value, Mapping):
            name = _first_mapping_value(value, ("name", "title", "identifier", "id"))
            if name is not None:
                return name
        elif value is not None:
            return value
    return None


def _values_for_keys(contexts: list[Mapping[str, Any]], keys: tuple[str, ...]) -> list[Any]:
    values: list[Any] = []
    for context in contexts:
        for key in keys:
            if key in context:
                values.append(context[key])
    return values


def _string_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, Mapping):
        value = _first_mapping_value(value, ("name", "title", "identifier", "id"))
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def _normalize(value: Any) -> str:
    text = _string_value(value)
    if not text:
        return ""
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def main() -> int:
    """Read an event JSON payload from stdin and print the title update action."""
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as error:
        print(json.dumps({"error": f"Invalid JSON: {error}"}), file=sys.stderr)
        return 1

    action = build_issue_title_update(event)
    print(json.dumps(action))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
