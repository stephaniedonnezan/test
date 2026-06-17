"""Build Linear issue-title updates for Cursor research automations.

The automation receives Linear/Cursor webhook payloads and returns a small
action object for the caller to apply. Payloads that are not status changes to
the "to research" workflow state are ignored.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow_state"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue title update action for matching Linear events.

    The returned shape is intentionally transport-agnostic so an automation
    runner can decide how to apply it to Linear:

    {
        "action": "update_issue_title",
        "issueId": "POI-123",
        "title": "Cursor researching: Existing title",
    }
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    new_status = _extract_new_status(event)
    if _normalize_text(new_status) != TARGET_STATUS:
        return None

    issue_id = _extract_issue_id(event)
    title = _extract_title(event)
    if not issue_id or not title:
        return None

    clean_title = title.strip()
    if clean_title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {clean_title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    event_names = {
        _normalize_text(value)
        for payload in _iter_mappings(event)
        for key, value in payload.items()
        if key in {"trigger", "action", "type", "webhookType", "webhook_type", "eventType"}
        and isinstance(value, str)
    }

    if any(_is_direct_status_change(name) for name in event_names):
        return True

    generic_updates = {"update", "updated", "issue update", "issue updated", "updated issue"}
    return bool(event_names & generic_updates) and _updated_fields_include_status(event)


def _is_direct_status_change(name: str) -> bool:
    if not name:
        return False

    words = set(name.split())
    return (
        "status" in words
        and ("changed" in words or "change" in words)
    ) or (
        "state" in words
        and ("changed" in words or "change" in words)
    )


def _updated_fields_include_status(event: Mapping[str, Any]) -> bool:
    for payload in _iter_mappings(event):
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            fields = payload.get(key)
            if isinstance(fields, str) and _is_status_field(fields):
                return True
            if isinstance(fields, Iterable) and not isinstance(fields, (str, bytes, Mapping)):
                if any(_is_status_field(str(field)) for field in fields):
                    return True

        for key in ("changes", "updatedFrom", "updated_from"):
            changes = payload.get(key)
            if isinstance(changes, Mapping) and any(_is_status_field(str(field)) for field in changes):
                return True

    return False


def _extract_new_status(event: Mapping[str, Any]) -> str | None:
    for payload in _iter_mappings(event):
        status = _first_string(
            payload,
            (
                "newStatus",
                "new_status",
                "newState",
                "new_state",
                "newWorkflowState",
                "new_workflow_state",
            ),
        )
        if status:
            return status

    for payload in _iter_mappings(event):
        changes = payload.get("changes")
        if isinstance(changes, Mapping):
            status = _status_from_changes(changes)
            if status:
                return status

    for payload in _preferred_issue_contexts(event):
        for key in ("status", "state", "workflowState", "workflow_state"):
            status = _string_from_value(payload.get(key))
            if status:
                return status

    return None


def _status_from_changes(changes: Mapping[str, Any]) -> str | None:
    for field, change in changes.items():
        if not _is_status_field(str(field)):
            continue

        if isinstance(change, Mapping):
            for key in ("new", "to", "after", "current", "value", "name"):
                status = _string_from_value(change.get(key))
                if status:
                    return status
        else:
            status = _string_from_value(change)
            if status:
                return status

    return None


def _extract_issue_id(event: Mapping[str, Any]) -> str | None:
    for payload in _preferred_issue_contexts(event):
        issue_id = _first_string(payload, ("issueId", "issue_id", "identifier", "key", "id"))
        if issue_id:
            return issue_id
    return None


def _extract_title(event: Mapping[str, Any]) -> str | None:
    for payload in _preferred_issue_contexts(event):
        title = _first_string(payload, ("title",))
        if title:
            return title
    return None


def _preferred_issue_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        contexts.append(trigger_context)

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            contexts.append(issue)
        contexts.append(data)

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        contexts.append(issue)

    contexts.append(event)
    return contexts


def _iter_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for child in value.values():
            yield from _iter_mappings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_mappings(child)


def _first_string(payload: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for key in keys:
        value = _string_from_value(payload.get(key))
        if value:
            return value
    return None


def _string_from_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            nested_value = _string_from_value(value.get(key))
            if nested_value:
                return nested_value
    return None


def _is_status_field(value: str) -> bool:
    normalized = _normalize_field_name(value)
    return normalized in STATUS_FIELD_NAMES


def _normalize_field_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""

    text = str(value).strip()
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
