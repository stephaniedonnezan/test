"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections import deque
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_KEYS = {"status", "state", "workflowstate", "workflow state"}
_STATUS_CHANGE_TRIGGERS = {
    "status changed",
    "status change",
    "statuschanged",
    "statuschange",
}
_UPDATE_ACTIONS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
    "issueupdated",
    "updatedissue",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear issue-title update action when an issue enters research."""

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    new_status = _extract_new_status(event)
    if _canonical(new_status) != _canonical(TARGET_STATUS):
        return None

    issue_id = _extract_issue_id(event)
    title = _extract_title(event)
    if not issue_id or not title:
        return None

    stripped_title = title.strip()
    if stripped_title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {stripped_title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    trigger_values = [
        value
        for mapping in _event_contexts(event)
        for key in ("trigger", "webhookType", "action", "type", "eventType")
        if (value := mapping.get(key)) is not None
    ]

    normalized_triggers = {_normalized_text(value) for value in trigger_values}
    if normalized_triggers & _STATUS_CHANGE_TRIGGERS:
        return True

    if normalized_triggers & _UPDATE_ACTIONS:
        return _has_updated_status_field(event)

    return False


def _has_updated_status_field(event: Mapping[str, Any]) -> bool:
    for mapping in _event_contexts(event):
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            if _contains_status_field(mapping.get(key)):
                return True

        for key in ("updatedFrom", "updated_from", "changes", "changed"):
            value = mapping.get(key)
            if isinstance(value, Mapping) and _contains_status_field(value.keys()):
                return True

    return False


def _contains_status_field(fields: Any) -> bool:
    if isinstance(fields, str):
        candidates: Iterable[Any] = (fields,)
    elif isinstance(fields, Mapping):
        candidates = fields.keys()
    elif isinstance(fields, Iterable):
        candidates = fields
    else:
        return False

    for field in candidates:
        normalized = _normalized_text(field)
        compact = _canonical(field)
        if normalized in _STATUS_FIELD_KEYS or compact in _STATUS_FIELD_KEYS:
            return True

    return False


def _extract_new_status(event: Mapping[str, Any]) -> str | None:
    explicit_keys = (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "newWorkflowState",
        "new_workflow_state",
    )
    current_keys = ("status", "state", "workflowState", "workflow_state")

    for mapping in _event_contexts(event):
        value = _first_value(mapping, explicit_keys)
        if value is not None:
            return _status_name(value)

    for mapping in _event_contexts(event):
        value = _first_value(mapping, current_keys)
        if value is not None:
            return _status_name(value)

    return None


def _extract_issue_id(event: Mapping[str, Any]) -> str | None:
    issue_sources = _issue_sources(event)
    for mapping in issue_sources:
        value = _first_value(mapping, ("issueId", "issue_id", "identifier", "id"))
        if isinstance(value, str) and value.strip():
            return value

    value = _first_value(event, ("issueId", "issue_id", "identifier"))
    if isinstance(value, str) and value.strip():
        return value

    return None


def _extract_title(event: Mapping[str, Any]) -> str | None:
    for mapping in _issue_sources(event):
        value = _first_value(mapping, ("title", "issueTitle", "issue_title", "name"))
        if isinstance(value, str) and value.strip():
            return value

    value = _first_value(event, ("title", "issueTitle", "issue_title"))
    if isinstance(value, str) and value.strip():
        return value

    return None


def _issue_sources(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    sources: list[Mapping[str, Any]] = []
    for key in ("triggerContext", "issue", "data"):
        value = event.get(key)
        if isinstance(value, Mapping):
            sources.append(value)
            nested_issue = value.get("issue")
            if isinstance(nested_issue, Mapping):
                sources.append(nested_issue)

    nested_data = event.get("data")
    if isinstance(nested_data, Mapping):
        for key in ("node", "entity"):
            value = nested_data.get(key)
            if isinstance(value, Mapping):
                sources.append(value)

    return sources


def _event_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []
    queue: deque[Mapping[str, Any]] = deque([event])

    while queue:
        current = queue.popleft()
        contexts.append(current)
        for key in ("triggerContext", "data", "issue", "node", "entity"):
            value = current.get(key)
            if isinstance(value, Mapping):
                queue.append(value)

    return contexts


def _first_value(mapping: Mapping[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        if key in mapping:
            return mapping[key]
    return None


def _status_name(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        for key in ("name", "title", "status", "state"):
            nested = value.get(key)
            if isinstance(nested, str):
                return nested
    return None


def _normalized_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def _canonical(value: Any) -> str:
    return _normalized_text(value).replace(" ", "")


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        json.dump(update, sys.stdout)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
