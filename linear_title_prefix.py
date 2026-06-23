"""Build Linear issue-title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
ACTION = "update_issue_title"
TARGET_STATUS = "toresearch"

_CAMEL_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return an issue-title update action when an issue moves to To Research.

    The automation payloads used in Cursor Cloud and Linear webhooks have a few
    different shapes. This function accepts the flat triggerContext form, nested
    automation_trigger_info forms, and typical Linear issue update payloads.
    """

    if not isinstance(event, Mapping):
        return None

    payloads = _payloads(event)
    if not _is_status_change(payloads):
        return None

    status = _target_status(payloads)
    if _normalize(status) != TARGET_STATUS:
        return None

    issue_id = _first_text(payloads, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_text(payloads, ("title", "issueTitle", "issue_title"))
    if not issue_id or not title:
        return None

    trimmed_title = title.strip()
    if _has_prefix(trimmed_title):
        return None

    return {
        "action": ACTION,
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {trimmed_title}",
    }


def _payloads(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    payloads: list[Mapping[str, Any]] = []

    def append(value: Any) -> None:
        if isinstance(value, Mapping) and value not in payloads:
            payloads.append(value)

    append(_mapping_at(event, ("automation_trigger_info", "triggerContext")))
    append(_mapping_at(event, ("automationTriggerInfo", "triggerContext")))
    append(_mapping_at(event, ("triggerContext",)))
    append(_mapping_at(event, ("data", "issue")))
    append(_mapping_at(event, ("data",)))
    append(_mapping_at(event, ("issue",)))
    append(event)

    return payloads


def _mapping_at(value: Mapping[str, Any], path: tuple[str, ...]) -> Mapping[str, Any] | None:
    current: Any = value
    for key in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current if isinstance(current, Mapping) else None


def _is_status_change(payloads: Iterable[Mapping[str, Any]]) -> bool:
    trigger_values = (
        "trigger",
        "webhookType",
        "webhook_type",
        "action",
        "type",
        "eventType",
        "event_type",
    )
    direct_status_events = {
        "statuschanged",
        "statuschange",
        "statechanged",
        "statechange",
        "workflowstatechanged",
        "workflowstatechange",
    }
    generic_issue_update_events = {
        "issueupdated",
        "updatedissue",
        "update",
        "updated",
        "issueupdate",
    }

    saw_generic_update = False
    for payload in payloads:
        for key in trigger_values:
            normalized = _normalize(payload.get(key))
            if normalized in direct_status_events:
                return True
            if normalized in generic_issue_update_events:
                saw_generic_update = True

    return saw_generic_update and _updated_fields_include_status(payloads)


def _updated_fields_include_status(payloads: Iterable[Mapping[str, Any]]) -> bool:
    watched_fields = {"status", "state", "workflowstate"}

    for payload in payloads:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            fields = payload.get(key)
            if isinstance(fields, str):
                if _normalize(fields) in watched_fields:
                    return True
            elif isinstance(fields, Iterable) and not isinstance(fields, (str, bytes, Mapping)):
                if any(_normalize(field) in watched_fields for field in fields):
                    return True

        changes = payload.get("changes")
        if isinstance(changes, Mapping):
            if any(_normalize(key) in watched_fields for key in changes):
                return True

    return False


def _target_status(payloads: Iterable[Mapping[str, Any]]) -> str | None:
    explicit_status_keys = (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "newWorkflowState",
        "new_workflow_state",
        "targetStatus",
        "target_status",
        "toStatus",
        "to_status",
    )
    fallback_status_keys = ("status", "state", "workflowState", "workflow_state")

    for payload in payloads:
        status = _first_status(payload, explicit_status_keys)
        if status:
            return status

    status_from_changes = _status_from_changes(payloads)
    if status_from_changes:
        return status_from_changes

    for payload in payloads:
        status = _first_status(payload, fallback_status_keys)
        if status:
            return status

    return None


def _status_from_changes(payloads: Iterable[Mapping[str, Any]]) -> str | None:
    for payload in payloads:
        changes = payload.get("changes")
        if not isinstance(changes, Mapping):
            continue

        for key in ("status", "state", "workflowState", "workflow_state"):
            status = _status_text(changes.get(key))
            if status:
                return status

    return None


def _first_status(payload: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        status = _status_text(payload.get(key))
        if status:
            return status
    return None


def _status_text(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if not isinstance(value, Mapping):
        return None

    for key in ("newValue", "new_value", "to", "after", "name", "title"):
        status = _status_text(value.get(key))
        if status:
            return status

    return None


def _first_text(payloads: Iterable[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for payload in payloads:
        for key in keys:
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value
            if value is not None and not isinstance(value, (Mapping, list, tuple, set)):
                return str(value)
    return None


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def _normalize(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    text = _CAMEL_BOUNDARY.sub(" ", text)
    return _NON_ALNUM.sub("", text.lower())


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
