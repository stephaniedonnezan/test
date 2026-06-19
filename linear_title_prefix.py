"""Build Linear issue title updates for research status transitions.

The module is intentionally side-effect free: callers pass a Linear/Cursor
automation payload and receive the title update they should apply, or ``None``
when the event should be ignored.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


PREFIX = "Cursor researching"
PREFIXED_TITLE_RE = re.compile(rf"^\s*{re.escape(PREFIX)}\b", re.IGNORECASE)
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow state"}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return an issue title update when ``event`` moves an issue to research."""

    if not isinstance(event, Mapping):
        return None

    context = _event_context(event)
    if not _is_linear_event(context):
        return None

    if not _is_status_change_event(context):
        return None

    if _normalize(_new_status(context)) != TARGET_STATUS:
        return None

    issue_id = _issue_id(context)
    title = _issue_title(context)
    if not issue_id or not title or PREFIXED_TITLE_RE.match(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _event_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten common Cursor Cloud and Linear webhook wrappers.

    Outer fields intentionally win over nested issue fields for trigger metadata
    and explicit status values, because nested issue/status objects may describe
    the current object rather than the transition.
    """

    context: dict[str, Any] = {}

    automation_info = _mapping(event.get("automation_trigger_info"))
    if automation_info:
        context.update(_event_context(automation_info))

    trigger_context = _mapping(event.get("triggerContext"))
    if trigger_context:
        context.update(_event_context(trigger_context))

    data = _mapping(event.get("data"))
    if data:
        issue = _mapping(data.get("issue"))
        if issue:
            context.update(_event_context(issue))
        context.update(data)

    issue = _mapping(event.get("issue"))
    if issue:
        context.update(_event_context(issue))

    context.update(event)
    return context


def _is_linear_event(context: Mapping[str, Any]) -> bool:
    trigger_type = _normalize(context.get("triggerType"))
    source = _normalize(context.get("source"))
    webhook_type = _normalize(context.get("webhookType"))
    event_type = _normalize(context.get("type"))

    if trigger_type == "linear" or source == "linear":
        return True
    if webhook_type in {"issue", "linear issue"}:
        return True
    if event_type in {"issue", "linear issue"}:
        return True
    return bool(context.get("newStatus") or context.get("new_status"))


def _is_status_change_event(context: Mapping[str, Any]) -> bool:
    event_names = [
        context.get("trigger"),
        context.get("action"),
        context.get("type"),
        context.get("webhookType"),
        context.get("event"),
    ]
    normalized_names = {_normalize(name) for name in event_names if name}

    if normalized_names & {
        "status changed",
        "status change",
        "state changed",
        "state change",
        "workflow state changed",
        "workflow state change",
    }:
        return True

    if _changed_status_fields(context):
        return True

    # Some automation payloads only expose the destination status field.
    return bool(context.get("newStatus") or context.get("new_status"))


def _changed_status_fields(context: Mapping[str, Any]) -> bool:
    updated_fields = context.get("updatedFields") or context.get("updated_fields")
    if _sequence_contains_status_field(updated_fields):
        return True

    changed_fields = context.get("changedFields") or context.get("changed_fields")
    if _sequence_contains_status_field(changed_fields):
        return True

    changes = context.get("changes") or context.get("changed") or context.get("updatedFrom")
    if isinstance(changes, Mapping):
        return any(_normalize(key) in STATUS_FIELDS for key in changes)

    return False


def _sequence_contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize(value) in STATUS_FIELDS
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return any(_normalize(item) in STATUS_FIELDS for item in value)
    return False


def _new_status(context: Mapping[str, Any]) -> Any:
    for key in (
        "newStatus",
        "new_status",
        "statusName",
        "stateName",
        "workflowStateName",
    ):
        if context.get(key):
            return context[key]

    changes = context.get("changes") or context.get("changed")
    if isinstance(changes, Mapping):
        for key in ("status", "state", "workflowState", "workflow_state"):
            value = changes.get(key)
            if isinstance(value, Mapping):
                for destination_key in ("to", "new", "newValue", "after", "name"):
                    destination = value.get(destination_key)
                    if isinstance(destination, Mapping) and destination.get("name"):
                        return destination["name"]
                    if destination:
                        return destination
            elif value:
                return value

    for key in ("status", "state", "workflowState", "workflow_state"):
        value = context.get(key)
        if isinstance(value, Mapping):
            if value.get("name"):
                return value["name"]
        elif value:
            return value

    return None


def _issue_id(context: Mapping[str, Any]) -> str | None:
    for key in ("issueId", "issue_id", "identifier", "key", "id"):
        value = context.get(key)
        if value is not None:
            issue_id = str(value).strip()
            if issue_id:
                return issue_id
    return None


def _issue_title(context: Mapping[str, Any]) -> str | None:
    title = context.get("title")
    if title is None:
        return None
    title = str(title).strip()
    return title or None


def _mapping(value: Any) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None


def _normalize(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update:
        print(json.dumps(update, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
