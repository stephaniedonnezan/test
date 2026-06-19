"""Build Linear issue title updates for Cursor research automations."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELDS = {
    "status",
    "state",
    "stateid",
    "statustype",
    "workflowstate",
    "workflowstateid",
}

_STATUS_CHANGE_TRIGGERS = {
    "status changed",
    "status change",
    "status_changed",
    "status-change",
    "state changed",
    "state change",
    "state_changed",
    "state-change",
    "workflow state changed",
    "workflow state change",
    "workflow_state_changed",
    "workflow-state-changed",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear issue title update when an issue moves to To Research.

    The Cursor automation trigger exposes a flat ``triggerContext`` object, while
    Linear webhooks can nest issue data and change metadata. This function accepts
    both shapes and returns a small action payload for the caller to apply.
    """

    if not isinstance(event, Mapping):
        return None

    context = _mapping(event.get("triggerContext")) or event
    issue = _issue_payload(event, context)

    if not _status_change_indicated(event, context):
        return None

    new_status = _new_status(event, context, issue)
    if _normalize_status(new_status) != TARGET_STATUS:
        return None

    title = _first_text(
        context.get("title"),
        issue.get("title"),
        _mapping(event.get("data")).get("title"),
        event.get("title"),
    )
    issue_id = _first_text(
        context.get("issueId"),
        context.get("issueID"),
        context.get("identifier"),
        context.get("id"),
        issue.get("identifier"),
        issue.get("issueId"),
        issue.get("issueID"),
        issue.get("id"),
    )

    if title is None or issue_id is None:
        return None

    title = title.strip()
    issue_id = issue_id.strip()
    if not title or not issue_id or _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _issue_payload(event: Mapping[str, Any], context: Mapping[str, Any]) -> Mapping[str, Any]:
    for candidate in (
        context.get("issue"),
        _mapping(event.get("data")).get("issue"),
        event.get("issue"),
        event.get("data"),
    ):
        if isinstance(candidate, Mapping):
            return candidate
    return {}


def _status_change_indicated(*containers: Mapping[str, Any]) -> bool:
    for container in containers:
        for key in ("trigger", "webhookType", "action", "type", "eventType"):
            value = container.get(key)
            if _normalize_trigger(value) in _STATUS_CHANGE_TRIGGERS:
                return True

        if any(container.get(key) is not None for key in ("newStatus", "newState", "newWorkflowState")):
            return True

        for key in ("field", "fieldName", "changedField"):
            if _is_status_field(container.get(key)):
                return True

        for key in ("changedFields", "updatedFields"):
            fields = container.get(key)
            if isinstance(fields, str) and _is_status_field(fields):
                return True
            if isinstance(fields, Iterable) and not isinstance(fields, (str, bytes, Mapping)):
                if any(_is_status_field(field) for field in fields):
                    return True

        for key in ("changes", "updatedFrom", "previous", "previousValues"):
            changes = container.get(key)
            if isinstance(changes, Mapping) and any(_is_status_field(field) for field in changes):
                return True

    return False


def _new_status(
    event: Mapping[str, Any],
    context: Mapping[str, Any],
    issue: Mapping[str, Any],
) -> Any:
    direct_status = _first_value(
        context.get("newStatus"),
        context.get("newState"),
        context.get("newWorkflowState"),
        event.get("newStatus"),
        event.get("newState"),
        event.get("newWorkflowState"),
    )
    if direct_status is not None:
        return direct_status

    for container in (context, event):
        for key in ("changes", "updatedFields"):
            status = _status_from_change_map(container.get(key))
            if status is not None:
                return status

    return _first_value(
        context.get("status"),
        context.get("state"),
        context.get("workflowState"),
        issue.get("status"),
        issue.get("state"),
        issue.get("workflowState"),
    )


def _status_from_change_map(changes: Any) -> Any:
    if not isinstance(changes, Mapping):
        return None

    for field in ("status", "state", "workflowState"):
        if field not in changes:
            continue

        change = changes[field]
        if isinstance(change, Mapping):
            return _first_value(
                change.get("to"),
                change.get("new"),
                change.get("newValue"),
                change.get("after"),
                change.get("value"),
            )
        return change

    return None


def _normalize_status(value: Any) -> str | None:
    text = _status_text(value)
    if text is None:
        return None
    return re.sub(r"[\s_-]+", " ", text.strip()).casefold()


def _status_text(value: Any) -> str | None:
    if isinstance(value, Mapping):
        return _first_text(
            value.get("name"),
            value.get("title"),
            value.get("label"),
            value.get("status"),
            value.get("state"),
        )
    return _text(value)


def _normalize_trigger(value: Any) -> str | None:
    text = _text(value)
    if text is None:
        return None
    return re.sub(r"[\s_-]+", " ", text.strip()).casefold()


def _is_status_field(value: Any) -> bool:
    text = _text(value)
    if text is None:
        return False
    return re.sub(r"[\s_-]+", "", text.strip()).casefold() in _STATUS_FIELDS


def _has_prefix(title: str) -> bool:
    return title.strip().casefold().startswith(TITLE_PREFIX.casefold())


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def _first_value(*values: Any) -> Any:
    return next((value for value in values if value is not None), None)


def _first_text(*values: Any) -> str | None:
    for value in values:
        text = _status_text(value) if isinstance(value, Mapping) else _text(value)
        if text is not None and text.strip():
            return text
    return None


def _text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        return str(value)
    return None


def main() -> int:
    update = build_issue_title_update(json.load(sys.stdin))
    print(json.dumps(update or {}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
