"""Build Linear issue title updates for Cursor research status changes.

The automation platform applies the returned action to Linear. This module is
kept side-effect free so the trigger decision can be tested independently.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"

_STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflowstatus"}
_EXPLICIT_NEW_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "statusName",
    "status_name",
    "stateName",
    "state_name",
    "workflowStateName",
    "workflow_state_name",
)
_TRIGGER_KEYS = ("trigger", "webhookType", "action", "type", "eventType")
_DIRECT_STATUS_CHANGE_TRIGGERS = {
    "statuschanged",
    "statechanged",
    "workflowstatechanged",
    "workflowstatuschanged",
}
_GENERIC_UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issueupdated",
    "updatedissue",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue enters to research."""

    if not isinstance(event, Mapping):
        return None

    payloads = _candidate_payloads(event)
    if not _is_status_change_event(payloads):
        return None

    status = _extract_new_status(payloads)
    if _normalize_token(status) != _normalize_token(TARGET_STATUS):
        return None

    title = _extract_first_string(payloads, ("title", "name"))
    issue_id = _extract_first_string(
        payloads,
        ("issueId", "issue_id", "identifier", "key", "id"),
    )
    if not title or not issue_id:
        return None

    title = title.strip()
    issue_id = issue_id.strip()
    if not title or not issue_id or _has_research_prefix(title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _candidate_payloads(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return likely payload layers, ordered from trigger metadata to issue data."""

    payloads: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in payloads:
            payloads.append(value)

    add(event)
    add(event.get("triggerContext"))
    data = event.get("data")
    add(data)
    if isinstance(data, Mapping):
        add(data.get("issue"))
        add(data.get("state"))
        add(data.get("workflowState"))
    issue = event.get("issue")
    add(issue)
    if isinstance(issue, Mapping):
        add(issue.get("state"))
        add(issue.get("workflowState"))

    # Trigger fields usually live outside issue data; issue title/id usually live
    # inside it. Keep both available without requiring callers to pre-normalize.
    return payloads


def _is_status_change_event(payloads: list[Mapping[str, Any]]) -> bool:
    trigger_tokens = {
        _normalize_token(payload.get(key))
        for payload in payloads
        for key in _TRIGGER_KEYS
        if payload.get(key) is not None
    }

    if trigger_tokens & _DIRECT_STATUS_CHANGE_TRIGGERS:
        return True
    if trigger_tokens & _GENERIC_UPDATE_TRIGGERS:
        return _updated_fields_include_status(payloads) or _changes_include_status(payloads)
    return False


def _updated_fields_include_status(payloads: list[Mapping[str, Any]]) -> bool:
    for payload in payloads:
        updated_fields = payload.get("updatedFields")
        if isinstance(updated_fields, Mapping):
            field_names = updated_fields.keys()
        elif isinstance(updated_fields, (list, tuple, set)):
            field_names = updated_fields
        else:
            field_names = ()

        for field_name in field_names:
            if _normalize_field_name(field_name) in _STATUS_FIELD_NAMES:
                return True

    return False


def _changes_include_status(payloads: list[Mapping[str, Any]]) -> bool:
    for payload in payloads:
        changes = payload.get("changes")
        if not isinstance(changes, Mapping):
            continue

        for field_name in changes.keys():
            if _normalize_field_name(field_name) in _STATUS_FIELD_NAMES:
                return True

    return False


def _extract_new_status(payloads: list[Mapping[str, Any]]) -> str | None:
    for key in _EXPLICIT_NEW_STATUS_KEYS:
        value = _extract_first_string(payloads, (key,))
        if value:
            return value

    for payload in payloads:
        changes = payload.get("changes")
        if isinstance(changes, Mapping):
            value = _status_from_changes(changes)
            if value:
                return value

    for payload in payloads:
        for key in ("status", "state", "workflowState", "workflowStatus"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value
            if isinstance(value, Mapping):
                nested = _first_string(value, ("name", "title", "status", "state"))
                if nested:
                    return nested

    return None


def _status_from_changes(changes: Mapping[str, Any]) -> str | None:
    for field_name, change in changes.items():
        if _normalize_field_name(field_name) not in _STATUS_FIELD_NAMES:
            continue
        if isinstance(change, str) and change.strip():
            return change.strip()
        if isinstance(change, Mapping):
            value = _first_string(
                change,
                ("to", "new", "newValue", "new_value", "after", "name"),
            )
            if value:
                return value
            for key in ("to", "new", "newValue", "new_value", "after"):
                nested = change.get(key)
                if isinstance(nested, Mapping):
                    value = _first_string(nested, ("name", "title", "status"))
                    if value:
                        return value
    return None


def _extract_first_string(
    payloads: list[Mapping[str, Any]],
    keys: tuple[str, ...],
) -> str | None:
    for payload in payloads:
        value = _first_string(payload, keys)
        if value:
            return value
    return None


def _first_string(payload: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def _normalize_field_name(value: Any) -> str:
    return _normalize_token(value)


def _normalize_token(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def main() -> int:
    """Read a JSON event from stdin and print the title update action, if any."""

    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
