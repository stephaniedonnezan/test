"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "workflow state", "workflowstate"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when an issue is moved to research."""
    if not isinstance(event, Mapping):
        return None

    containers = _containers(event)
    if not _is_status_change_event(containers):
        return None

    status = _new_status(containers)
    if _normalize_words(status) != TARGET_STATUS:
        return None

    issue_id = _issue_id(containers)
    title = _issue_title(containers)
    if not issue_id or not title:
        return None

    if title.lower().startswith(PREFIX.lower()):
        updated_title = title
    else:
        updated_title = f"{PREFIX}: {title}"

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": updated_title,
    }


def _containers(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Collect likely metadata and issue objects without losing precedence."""
    containers: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in containers:
            containers.append(value)

    add(event.get("triggerContext"))
    add(event)
    add(event.get("data"))
    add(event.get("issue"))

    data = event.get("data")
    if isinstance(data, Mapping):
        add(data.get("issue"))
        add(data.get("state"))
        add(data.get("workflowState"))

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        add(trigger_context.get("data"))
        add(trigger_context.get("issue"))
        context_data = trigger_context.get("data")
        if isinstance(context_data, Mapping):
            add(context_data.get("issue"))

    return containers


def _is_status_change_event(containers: list[Mapping[str, Any]]) -> bool:
    trigger_values: list[str] = []
    for container in containers:
        for key in ("trigger", "webhookType", "action", "type", "eventType"):
            value = container.get(key)
            if isinstance(value, str):
                trigger_values.append(_normalize_words(value))

    if any(value in {"status changed", "status change"} for value in trigger_values):
        return True

    if any(value in {"issue updated", "updated issue", "update", "updated"} for value in trigger_values):
        return _has_status_change_marker(containers)

    return False


def _has_status_change_marker(containers: list[Mapping[str, Any]]) -> bool:
    for container in containers:
        updated_fields = container.get("updatedFields")
        if _field_list_mentions_status(updated_fields):
            return True

        changes = container.get("changes")
        if isinstance(changes, Mapping):
            if any(_normalize_words(key) in STATUS_FIELD_NAMES for key in changes):
                return True
        elif _field_list_mentions_status(changes):
            return True

        updated_from = container.get("updatedFrom")
        if isinstance(updated_from, Mapping):
            if any(_normalize_words(key) in STATUS_FIELD_NAMES for key in updated_from):
                return True

    return False


def _field_list_mentions_status(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_words(value) in STATUS_FIELD_NAMES
    if isinstance(value, list | tuple | set):
        return any(_field_list_mentions_status(item) for item in value)
    if isinstance(value, Mapping):
        return any(_normalize_words(key) in STATUS_FIELD_NAMES for key in value)
    return False


def _new_status(containers: list[Mapping[str, Any]]) -> Any:
    explicit_keys = (
        "newStatus",
        "new_status",
        "toStatus",
        "to_status",
        "newState",
        "new_state",
        "toState",
        "to_state",
        "statusName",
    )
    for container in containers:
        for key in explicit_keys:
            value = _name_value(container.get(key))
            if value:
                return value

        changes_status = _status_from_changes(container.get("changes"))
        if changes_status:
            return changes_status

    fallback_keys = ("status", "state", "workflowState", "workflow_state")
    for container in containers:
        for key in fallback_keys:
            value = _name_value(container.get(key))
            if value:
                return value

    return None


def _status_from_changes(changes: Any) -> Any:
    if not isinstance(changes, Mapping):
        return None

    for key, value in changes.items():
        if _normalize_words(key) not in STATUS_FIELD_NAMES:
            continue

        if isinstance(value, Mapping):
            for candidate in ("newValue", "new", "to", "after", "value", "name"):
                status = _name_value(value.get(candidate))
                if status:
                    return status
        else:
            status = _name_value(value)
            if status:
                return status

    return None


def _issue_id(containers: list[Mapping[str, Any]]) -> str | None:
    for key in ("issueId", "issue_id", "identifier", "key", "id"):
        for container in containers:
            value = container.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _issue_title(containers: list[Mapping[str, Any]]) -> str | None:
    for container in containers:
        value = container.get("title")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _name_value(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, Mapping):
        for key in ("name", "displayName", "title", "label"):
            named_value = value.get(key)
            if isinstance(named_value, str) and named_value.strip():
                return named_value.strip()
    return None


def _normalize_words(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def main() -> int:
    payload = json.load(sys.stdin)
    action = build_issue_title_update(payload)
    if action is not None:
        json.dump(action, sys.stdout, indent=2)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
