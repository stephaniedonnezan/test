"""Build Linear issue-title update actions for research status transitions.

The automation runner can pass slightly different webhook shapes depending on
where the event originated. This module keeps the business rule small:
when an issue status changes to "to research", prefix its title with
"Cursor researching".
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}
UPDATE_TRIGGERS = {"update", "updated", "issueupdate", "issueupdated", "updatedissue"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action for matching status changes.

    The returned action is intentionally side-effect free so callers can decide
    how to send the update to Linear.
    """

    if not isinstance(event, Mapping):
        return None

    payload = _payload(event)
    if not _is_status_change(payload):
        return None

    new_status = _new_status(payload)
    if _normalize(new_status) != _normalize(TARGET_STATUS):
        return None

    issue = _issue(payload)
    issue_id = _first_text(issue, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_text(issue, ("title", "name"))
    if not issue_id or not title or _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _payload(event: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten common Cursor and Linear webhook wrappers."""

    payload: dict[str, Any] = {}

    def merge(value: Any) -> None:
        if isinstance(value, Mapping):
            payload.update(value)

    trigger_context = event.get("triggerContext")
    automation_trigger_info = event.get("automation_trigger_info")
    data = event.get("data")
    issue = event.get("issue")

    if isinstance(automation_trigger_info, Mapping):
        merge(automation_trigger_info.get("triggerContext"))

    if isinstance(data, Mapping):
        merge(data)
        merge(data.get("issue"))

    merge(issue)
    merge(trigger_context)
    merge(event)

    if isinstance(automation_trigger_info, Mapping):
        merge(automation_trigger_info.get("triggerContext"))
    if isinstance(trigger_context, Mapping):
        merge(trigger_context)

    return payload


def _issue(payload: Mapping[str, Any]) -> dict[str, Any]:
    issue: dict[str, Any] = {}
    for key in ("data", "issue", "triggerContext"):
        value = payload.get(key)
        if isinstance(value, Mapping):
            issue.update(_issue(value))
            issue.update(value)
    issue.update(payload)
    return issue


def _is_status_change(payload: Mapping[str, Any]) -> bool:
    trigger_values = [
        payload.get(key)
        for key in ("trigger", "webhookType", "action", "type", "eventType")
        if key in payload
    ]

    if any(_is_direct_status_trigger(value) for value in trigger_values):
        return True

    if any(_normalize(value) in UPDATE_TRIGGERS for value in trigger_values):
        return _changed_status_field(payload)

    return _changed_status_field(payload)


def _is_direct_status_trigger(value: Any) -> bool:
    normalized = _normalize(value)
    return "statuschanged" in normalized or "statechanged" in normalized


def _changed_status_field(payload: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "changedFields"):
        if _contains_status_field(payload.get(key)):
            return True

    changes = payload.get("changes")
    if isinstance(changes, Mapping):
        return any(_is_status_field(key) for key in changes)
    if isinstance(changes, list):
        return any(_change_mentions_status(change) for change in changes)

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)
    if isinstance(value, list | tuple | set):
        return any(_contains_status_field(item) for item in value)
    return False


def _change_mentions_status(change: Any) -> bool:
    if isinstance(change, str):
        return _is_status_field(change)
    if isinstance(change, Mapping):
        return any(
            _is_status_field(change.get(key))
            for key in ("field", "fieldName", "name", "key", "property")
        )
    return False


def _is_status_field(value: Any) -> bool:
    return _normalize(value) in STATUS_FIELDS


def _new_status(payload: Mapping[str, Any]) -> str | None:
    for key in (
        "newStatus",
        "new_status",
        "toStatus",
        "to_status",
        "statusName",
        "stateName",
        "workflowStateName",
    ):
        text = _coerce_text(payload.get(key))
        if text:
            return text

    changes = payload.get("changes")
    status_from_changes = _status_from_changes(changes)
    if status_from_changes:
        return status_from_changes

    for key in ("status", "state", "workflowState", "workflow_state"):
        text = _name_or_text(payload.get(key))
        if text:
            return text

    return None


def _status_from_changes(changes: Any) -> str | None:
    if isinstance(changes, Mapping):
        for key, value in changes.items():
            if _is_status_field(key):
                text = _new_value(value)
                if text:
                    return text

    if isinstance(changes, list):
        for change in changes:
            if isinstance(change, Mapping) and _change_mentions_status(change):
                text = _new_value(change)
                if text:
                    return text

    return None


def _new_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("newValue", "new_value", "to", "after", "value", "name"):
            text = _name_or_text(value.get(key))
            if text:
                return text
        return None
    return _name_or_text(value)


def _first_text(payload: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        text = _coerce_text(payload.get(key))
        if text:
            return text
    return None


def _name_or_text(value: Any) -> str | None:
    if isinstance(value, Mapping):
        return _first_text(value, ("name", "title", "label"))
    return _coerce_text(value)


def _coerce_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize(value: Any) -> str:
    text = _coerce_text(value)
    if not text:
        return ""
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def _has_prefix(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())


def main() -> None:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
