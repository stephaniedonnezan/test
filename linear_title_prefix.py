"""Build Linear issue title updates for Cursor research automations."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow state"}
_DIRECT_STATUS_TRIGGERS = {
    "status change",
    "status changed",
    "status update",
    "status updated",
    "state change",
    "state changed",
    "workflow state change",
    "workflow state changed",
}
_UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue enters "to research".

    The Cursor automation payload can be either a flat trigger context or a
    nested Linear webhook-style payload. The returned action is intentionally
    side-effect free so callers can decide how to apply it.
    """

    if not isinstance(event, Mapping):
        return None

    payload = _flatten_payload(event)
    if not _is_status_change_event(payload):
        return None

    status = _new_status(payload)
    if _normalize(status) != TARGET_STATUS:
        return None

    issue_id = _first_text(payload, ("issueId", "issue_id", "id", "identifier", "key"))
    title = _first_text(payload, ("title", "name", "issueTitle"))
    if not issue_id or not title:
        return None

    if _has_prefix(title):
        new_title = title
    else:
        new_title = f"{PREFIX}: {title}"

    return {"action": "update_issue_title", "issueId": issue_id, "title": new_title}


def _flatten_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common nested Linear/Cursor payload locations into one mapping."""

    result: dict[str, Any] = {}

    for path in (
        ("data", "issue"),
        ("issue",),
        ("triggerContext",),
        ("data",),
    ):
        nested = _get_path(event, path)
        if isinstance(nested, Mapping):
            result.update(nested)

    result.update(event)

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        result.update(trigger_context)

    return result


def _get_path(event: Mapping[str, Any], path: tuple[str, ...]) -> Any:
    current: Any = event
    for key in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current


def _is_status_change_event(payload: Mapping[str, Any]) -> bool:
    trigger_values = [
        payload.get(key)
        for key in ("trigger", "webhookType", "action", "type", "eventType")
    ]
    normalized_triggers = {_normalize(value) for value in trigger_values if value is not None}

    if normalized_triggers & _DIRECT_STATUS_TRIGGERS:
        return True

    if normalized_triggers & _UPDATE_TRIGGERS:
        return _updated_status_field(payload)

    return False


def _updated_status_field(payload: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        fields = payload.get(key)
        if _contains_status_field(fields):
            return True

    changes = payload.get("changes")
    if isinstance(changes, Mapping):
        return any(_normalize(key) in _STATUS_FIELD_NAMES for key in changes)

    return False


def _contains_status_field(fields: Any) -> bool:
    if isinstance(fields, str):
        return _normalize(fields) in _STATUS_FIELD_NAMES

    if isinstance(fields, Mapping):
        return any(_normalize(key) in _STATUS_FIELD_NAMES for key in fields)

    if isinstance(fields, Iterable):
        return any(_normalize(field) in _STATUS_FIELD_NAMES for field in fields)

    return False


def _new_status(payload: Mapping[str, Any]) -> str:
    for key in (
        "newStatus",
        "new_status",
        "status",
        "state",
        "workflowState",
        "workflow_state",
    ):
        value = payload.get(key)
        text = _text(value)
        if text:
            return text

    changes = payload.get("changes")
    if isinstance(changes, Mapping):
        for key in ("status", "state", "workflowState", "workflow_state"):
            value = changes.get(key)
            if isinstance(value, Mapping):
                text = _first_text(value, ("new", "to", "after", "name"))
            else:
                text = _text(value)
            if text:
                return text

    return ""


def _first_text(payload: Mapping[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        text = _text(payload.get(key))
        if text:
            return text
    return ""


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, Mapping):
        return _first_text(value, ("name", "title", "id", "identifier", "key"))
    text = str(value).strip()
    return text


def _normalize(value: Any) -> str:
    text = _text(value)
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def _has_prefix(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        json.dump(action, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
