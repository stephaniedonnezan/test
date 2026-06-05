"""Build Linear issue title updates for research status transitions.

The automation runner can feed this module either the flat Cursor trigger
context or a nested Linear webhook payload.  When the event represents an
issue moving to "to research", the handler returns a small action payload that
the caller can use to update the issue title.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TITLE_PREFIX_WITH_SEPARATOR = f"{TITLE_PREFIX}: "
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflowstate",
    "workflowstatus",
}

_DIRECT_STATUS_CHANGE_EVENTS = {
    "status changed",
    "status change",
    "issue status changed",
    "issue status change",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
}

_ISSUE_UPDATE_EVENTS = {
    "issue updated",
    "updated issue",
    "update issue",
    "issue update",
    "update",
    "updated",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title-update action when a Linear issue enters research.

    The returned payload is intentionally side-effect free:

    {
        "action": "update_issue_title",
        "issueId": "<issue id or identifier>",
        "title": "Cursor researching: <existing title>",
    }
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    if _normalize_status(_new_status(event)) != TARGET_STATUS:
        return None

    issue_id = _first_text(_issue_payloads(event), ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_text(_issue_payloads(event), ("title", "issueTitle", "issue_title"))

    if not issue_id or not title or _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX_WITH_SEPARATOR}{title.strip()}",
    }


def handle_issue_status_changed(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Compatibility wrapper for automation entrypoints."""

    return build_issue_title_update(event)


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    for payload in _event_payloads(event):
        for key in ("trigger", "webhookType", "webhook_type", "event", "action", "type"):
            normalized = _normalize_token(payload.get(key))
            if normalized in _DIRECT_STATUS_CHANGE_EVENTS:
                return True
            if normalized in _ISSUE_UPDATE_EVENTS and _has_status_update_marker(event):
                return True

    return _has_status_update_marker(event)


def _has_status_update_marker(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized_key = _normalize_field_name(key)
            if normalized_key == "updatedfields":
                if _contains_status_field(item):
                    return True
            if normalized_key in {"changes", "change", "updatedfrom"}:
                if _mapping_mentions_status_field(item):
                    return True
            if _has_status_update_marker(item):
                return True

    if isinstance(value, list | tuple):
        return any(_has_status_update_marker(item) for item in value)

    return False


def _new_status(event: Mapping[str, Any]) -> Any:
    for payload in _event_payloads(event):
        for key in (
            "newStatus",
            "new_status",
            "toStatus",
            "to_status",
            "statusName",
            "stateName",
            "workflowStateName",
        ):
            if key in payload:
                return payload[key]

    changed_status = _status_from_changes(event)
    if changed_status is not None:
        return changed_status

    for payload in _issue_payloads(event):
        for key in ("status", "state", "workflowState", "workflow_state"):
            if key in payload:
                return _name_value(payload[key])

    for payload in _event_payloads(event):
        if "status" in payload:
            return _name_value(payload["status"])

    return None


def _status_from_changes(value: Any) -> Any:
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized_key = _normalize_field_name(key)
            if normalized_key in {"changes", "change"}:
                changed = _changed_status_value(item)
                if changed is not None:
                    return changed
            if normalized_key != "updatedfrom":
                changed = _status_from_changes(item)
                if changed is not None:
                    return changed

    if isinstance(value, list | tuple):
        for item in value:
            changed = _status_from_changes(item)
            if changed is not None:
                return changed

    return None


def _changed_status_value(changes: Any) -> Any:
    if isinstance(changes, Mapping):
        for key, item in changes.items():
            if _normalize_field_name(key) in _STATUS_FIELD_NAMES:
                return _new_value_from_change(item)

    if isinstance(changes, list | tuple):
        for item in changes:
            if not isinstance(item, Mapping):
                continue
            field = item.get("field") or item.get("fieldName") or item.get("name")
            if _normalize_field_name(field) in _STATUS_FIELD_NAMES:
                return _new_value_from_change(item)

    return None


def _new_value_from_change(change: Any) -> Any:
    if not isinstance(change, Mapping):
        return change

    for key in ("to", "toValue", "newValue", "new", "after", "current"):
        if key in change:
            return _name_value(change[key])

    return None


def _event_payloads(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    payloads: list[Mapping[str, Any]] = [event]
    for key in ("triggerContext", "trigger_context", "webhook", "data"):
        item = event.get(key)
        if isinstance(item, Mapping):
            payloads.append(item)
    return payloads


def _issue_payloads(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    payloads: list[Mapping[str, Any]] = []

    for key in ("triggerContext", "trigger_context"):
        item = event.get(key)
        if isinstance(item, Mapping):
            payloads.append(item)

    data = event.get("data")
    if isinstance(data, Mapping):
        for key in ("issue", "node"):
            item = data.get(key)
            if isinstance(item, Mapping):
                payloads.append(item)
        payloads.append(data)

    for key in ("issue", "node", "resource"):
        item = event.get(key)
        if isinstance(item, Mapping):
            payloads.append(item)

    payloads.append(event)
    return payloads


def _first_text(payloads: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for payload in payloads:
        for key in keys:
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_field_name(value) in _STATUS_FIELD_NAMES

    if isinstance(value, Mapping):
        if "field" in value and _contains_status_field(value["field"]):
            return True
        return any(_contains_status_field(item) for item in value.values())

    if isinstance(value, list | tuple | set):
        return any(_contains_status_field(item) for item in value)

    return False


def _mapping_mentions_status_field(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(_normalize_field_name(key) in _STATUS_FIELD_NAMES for key in value)

    if isinstance(value, list | tuple):
        return any(_contains_status_field(item) for item in value)

    return False


def _name_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        for key in ("name", "title", "label", "value"):
            if key in value:
                return value[key]
    return value


def _has_research_prefix(title: str) -> bool:
    return title.lstrip().casefold().startswith(TITLE_PREFIX.casefold())


def _normalize_status(value: Any) -> str | None:
    normalized = _normalize_token(_name_value(value))
    return normalized or None


def _normalize_field_name(value: Any) -> str:
    return _normalize_token(value).replace(" ", "")


def _normalize_token(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    value = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    value = re.sub(r"[_\-/]+", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip().casefold()


def main() -> int:
    event = json.load(sys.stdin)
    result = build_issue_title_update(event)
    print(json.dumps(result, indent=2, sort_keys=True) if result else "null")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
