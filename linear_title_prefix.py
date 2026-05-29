"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow status"}
STATUS_NAME_KEYS = (
    "newStatus",
    "new_status",
    "statusName",
    "status_name",
    "newState",
    "new_state",
)
TRIGGER_KEYS = ("trigger", "webhookType", "action", "type")


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return an issue title update action when an issue enters To Research."""
    if not isinstance(event, Mapping):
        return None

    context = _event_context(event)
    if not _is_status_change_event(context):
        return None

    status = _extract_new_status(context)
    if _normalize_text(status) != TARGET_STATUS:
        return None

    issue = _issue_payload(context)
    issue_id = _first_text(issue, ("id", "issueId", "issue_id", "identifier"))
    title = _first_text(issue, ("title",))
    if not issue_id or not title:
        return None

    if title.casefold().startswith(PREFIX.casefold()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _event_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common Cursor and Linear webhook nesting into a single context."""
    context: dict[str, Any] = {}

    for key in ("triggerContext", "webhook", "payload", "data"):
        value = event.get(key)
        if isinstance(value, Mapping):
            context.update(value)

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            context.update(issue)
        context.update(data)

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        context.update(issue)

    context.update(event)
    return context


def _issue_payload(context: Mapping[str, Any]) -> Mapping[str, Any]:
    data = context.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            return issue

    issue = context.get("issue")
    if isinstance(issue, Mapping):
        return issue

    return context


def _is_status_change_event(context: Mapping[str, Any]) -> bool:
    trigger_values = [_normalize_text(context.get(key)) for key in TRIGGER_KEYS]
    if any(value in {"status changed", "status change", "state changed", "workflow state changed"} for value in trigger_values):
        return True

    if any(value in {"issue updated", "updated issue", "update", "updated"} for value in trigger_values):
        return _has_status_update_marker(context)

    return False


def _has_status_update_marker(context: Mapping[str, Any]) -> bool:
    updated_fields = context.get("updatedFields") or context.get("updated_fields")
    if _contains_status_field(updated_fields):
        return True

    for key in ("updatedFrom", "updated_from", "changes", "changedFields", "changed_fields"):
        value = context.get(key)
        if _contains_status_field(value):
            return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_field(value) in STATUS_FIELDS

    if isinstance(value, Mapping):
        return any(_normalize_field(key) in STATUS_FIELDS for key in value)

    if isinstance(value, list | tuple | set):
        return any(_contains_status_field(item) for item in value)

    return False


def _extract_new_status(context: Mapping[str, Any]) -> str | None:
    status = _first_text(context, STATUS_NAME_KEYS)
    if status:
        return status

    for key in ("state", "workflowState", "workflow_state", "status"):
        value = context.get(key)
        if isinstance(value, Mapping):
            name = _first_text(value, ("name", "title"))
            if name:
                return name
        elif isinstance(value, str):
            return value

    data = context.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            return _extract_new_status(issue)

    issue = context.get("issue")
    if isinstance(issue, Mapping):
        return _extract_new_status(issue)

    return None


def _first_text(payload: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str):
            text = value.strip()
            if text:
                return text
    return None


def _normalize_field(value: Any) -> str:
    text = _normalize_text(value)
    return text.replace(" ", "")


def _normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value.strip())
    text = re.sub(r"[_\-/]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.casefold()


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action:
        print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
