"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}
STATUS_CHANGE_TRIGGERS = {
    "status changed",
    "status change",
    "state changed",
    "workflow state changed",
}
ISSUE_UPDATE_TRIGGERS = {
    "issue updated",
    "updated issue",
    "update",
    "updated",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue enters research status.

    The Cursor automation payload is usually flat under ``triggerContext``. This
    also accepts common nested Linear webhook shapes so tests can exercise the
    same normalization that production integrations tend to need.
    """

    if not isinstance(event, Mapping):
        return None

    payload = _flatten_event(event)

    if not _is_status_change_event(payload):
        return None

    status = _extract_status(payload)
    if _normalize_text(status) != TARGET_STATUS:
        return None

    issue_id = _first_text(payload, ("issueId", "issue_id", "id", "identifier", "key"))
    title = _first_text(payload, ("title", "name"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _flatten_event(event: Mapping[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}

    for key in ("issue", "data", "triggerContext"):
        nested = event.get(key)
        if isinstance(nested, Mapping):
            payload.update(_flatten_event(nested))

    payload.update(event)
    return payload


def _is_status_change_event(payload: Mapping[str, Any]) -> bool:
    trigger_values = [
        _normalize_text(payload.get(key))
        for key in ("trigger", "webhookType", "action", "type")
        if payload.get(key) is not None
    ]

    if any(value in STATUS_CHANGE_TRIGGERS for value in trigger_values):
        return True

    if any(value in ISSUE_UPDATE_TRIGGERS for value in trigger_values):
        return _updated_fields_include_status(payload)

    return False


def _updated_fields_include_status(payload: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields"):
        fields = payload.get(key)
        if isinstance(fields, str):
            field_values = re.split(r"[, ]+", fields)
        elif isinstance(fields, Sequence) and not isinstance(fields, (str, bytes)):
            field_values = fields
        else:
            continue

        for field in field_values:
            if _normalize_field_name(field) in STATUS_FIELDS:
                return True

    changes = payload.get("changes")
    if isinstance(changes, Mapping):
        return any(_normalize_field_name(field) in STATUS_FIELDS for field in changes)

    return False


def _extract_status(payload: Mapping[str, Any]) -> str | None:
    status = _first_text(
        payload,
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
    if status:
        return status

    for key in ("status", "state", "workflowState", "workflow_state"):
        value = payload.get(key)
        if isinstance(value, Mapping):
            status = _first_text(value, ("name", "title", "id"))
            if status:
                return status
        elif isinstance(value, str):
            return value

    changes = payload.get("changes")
    if isinstance(changes, Mapping):
        for key in ("status", "state", "workflowState", "workflow_state"):
            status = _status_from_change(changes.get(key))
            if status:
                return status

    return None


def _status_from_change(change: Any) -> str | None:
    if isinstance(change, str):
        return change

    if not isinstance(change, Mapping):
        return None

    for key in ("to", "new", "newValue", "after"):
        value = change.get(key)
        if isinstance(value, Mapping):
            status = _first_text(value, ("name", "title", "id"))
            if status:
                return status
        elif isinstance(value, str):
            return value

    return _first_text(change, ("name", "title"))


def _first_text(payload: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value

    return None


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def _normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    normalized = re.sub(r"[^a-z0-9]+", " ", spaced.lower()).strip()
    return re.sub(r"\s+", " ", normalized)


def _normalize_field_name(value: Any) -> str:
    return _normalize_text(value).replace(" ", "")


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
