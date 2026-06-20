"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow status"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to research."""

    if not isinstance(event, Mapping):
        return None

    contexts = _context_candidates(event)
    if not contexts:
        return None

    if not any(_is_status_change_context(context) for context in contexts):
        return None

    new_status = _first_text(
        _status_values_from_changes(contexts),
        _values_for_keys(contexts, ("newStatus", "new_status", "toStatus", "to_status")),
        _nested_name_values(contexts, ("status", "state", "workflowState", "workflow_state")),
        _values_for_keys(contexts, ("status", "state", "workflowState", "workflow_state")),
    )
    if _normalize_text(new_status) != _normalize_text(TARGET_STATUS):
        return None

    issue_id = _first_text(
        _values_for_keys(contexts, ("issueId", "issue_id", "identifier", "key", "id"))
    )
    title = _first_text(_values_for_keys(contexts, ("title", "name")))
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


def _context_candidates(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return payload sections ordered from outer metadata to issue details."""

    candidates: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in candidates:
            candidates.append(value)

    add(event)
    add(event.get("triggerContext"))

    automation_info = event.get("automation_trigger_info")
    if isinstance(automation_info, Mapping):
        add(automation_info)
        add(automation_info.get("triggerContext"))

    data = event.get("data")
    add(data)
    if isinstance(data, Mapping):
        add(data.get("issue"))
        add(data.get("triggerContext"))

    issue = event.get("issue")
    add(issue)

    return candidates


def _is_status_change_context(context: Mapping[str, Any]) -> bool:
    event_names = _values_for_keys(
        (context,), ("trigger", "webhookType", "action", "type", "event")
    )
    if any(_is_direct_status_change_name(value) for value in event_names):
        return True

    if any(_is_issue_update_name(value) for value in event_names):
        return _changed_status_field(context)

    return False


def _is_direct_status_change_name(value: Any) -> bool:
    normalized = _normalize_text(value)
    return normalized in {
        "status changed",
        "state changed",
        "workflow state changed",
        "workflow status changed",
    }


def _is_issue_update_name(value: Any) -> bool:
    normalized = _normalize_text(value)
    return normalized in {
        "update",
        "updated",
        "issue update",
        "issue updated",
        "updated issue",
    }


def _changed_status_field(context: Mapping[str, Any]) -> bool:
    fields = context.get("updatedFields")
    if isinstance(fields, str):
        fields = [fields]
    if isinstance(fields, list) and any(_is_status_field_name(field) for field in fields):
        return True

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        return any(_is_status_field_name(key) for key in changes)
    if isinstance(changes, list):
        return any(_change_names_status_field(change) for change in changes)

    return False


def _change_names_status_field(change: Any) -> bool:
    if isinstance(change, str):
        return _is_status_field_name(change)
    if not isinstance(change, Mapping):
        return False
    return any(
        _is_status_field_name(change.get(key))
        for key in ("field", "fieldName", "name", "property", "key")
    )


def _is_status_field_name(value: Any) -> bool:
    return _normalize_text(value) in STATUS_FIELD_NAMES


def _status_values_from_changes(contexts: list[Mapping[str, Any]]) -> list[Any]:
    values: list[Any] = []
    for context in contexts:
        changes = context.get("changes")
        if isinstance(changes, Mapping):
            for key, change in changes.items():
                if _is_status_field_name(key):
                    values.extend(_destination_values(change))
        elif isinstance(changes, list):
            for change in changes:
                if _change_names_status_field(change):
                    values.extend(_destination_values(change))
    return values


def _destination_values(change: Any) -> list[Any]:
    if isinstance(change, Mapping):
        return [
            change.get(key)
            for key in ("to", "toValue", "newValue", "after", "value", "name")
            if key in change
        ]
    return [change]


def _values_for_keys(contexts: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...], keys: tuple[str, ...]) -> list[Any]:
    values: list[Any] = []
    for context in contexts:
        for key in keys:
            if key in context:
                values.append(context[key])
    return values


def _nested_name_values(contexts: list[Mapping[str, Any]], keys: tuple[str, ...]) -> list[Any]:
    values: list[Any] = []
    for context in contexts:
        for key in keys:
            nested = context.get(key)
            if isinstance(nested, Mapping):
                values.extend(_values_for_keys((nested,), ("name", "title", "id")))
    return values


def _first_text(*groups: list[Any]) -> str | None:
    for group in groups:
        for value in group:
            text = _stringify_status_value(value)
            if text:
                return text
    return None


def _stringify_status_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        return _first_text(_values_for_keys((value,), ("name", "title", "id")))
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.casefold().split())


def main() -> int:
    payload = json.load(sys.stdin)
    action = build_issue_title_update(payload)
    if action is not None:
        json.dump(action, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
