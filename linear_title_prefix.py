"""Build Linear issue title updates for research-status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflowstate",
    "workflowstatus",
}
_TRIGGER_FIELD_NAMES = {"trigger", "webhooktype", "action", "type"}
_DIRECT_STATUS_CHANGE_TRIGGERS = {
    "status changed",
    "status change",
    "statuschanged",
    "state changed",
    "state change",
    "statechanged",
    "workflow state changed",
    "workflowstate changed",
}
_GENERIC_UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title-update action when an issue enters research status.

    The returned action is intentionally side-effect free:

    ``{"action": "update_issue_title", "issueId": "...", "title": "..."}``

    A caller that has Linear credentials can execute that action separately.
    """

    if not isinstance(event, Mapping):
        return None

    payloads = list(_candidate_payloads(event))
    if not _is_status_transition(payloads):
        return None

    status = _new_status(payloads)
    if _normalize(status) != TARGET_STATUS:
        return None

    issue_id = _first_string(payloads, ("issueId", "issue_id", "id", "identifier", "key"))
    title = _first_string(payloads, ("title", "name"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _candidate_payloads(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield useful payload layers from outermost metadata to nested issue data."""

    yield event

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        yield trigger_context

    data = event.get("data")
    if isinstance(data, Mapping):
        yield data

        issue = data.get("issue")
        if isinstance(issue, Mapping):
            yield issue

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        yield issue


def _is_status_transition(payloads: list[Mapping[str, Any]]) -> bool:
    trigger_values = {
        _normalize(value)
        for payload in payloads
        for key, value in payload.items()
        if _field_name(key) in _TRIGGER_FIELD_NAMES and isinstance(value, str)
    }

    if trigger_values & _DIRECT_STATUS_CHANGE_TRIGGERS:
        return True

    if trigger_values & _GENERIC_UPDATE_TRIGGERS:
        return _changed_fields_include_status(payloads)

    return _changed_fields_include_status(payloads)


def _changed_fields_include_status(payloads: list[Mapping[str, Any]]) -> bool:
    for payload in payloads:
        for key in ("updatedFields", "changedFields", "changes"):
            value = payload.get(key)
            if _contains_status_field(value):
                return True

        updated_from = payload.get("updatedFrom")
        if isinstance(updated_from, Mapping) and _contains_status_field(updated_from):
            return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _field_name(value) in _STATUS_FIELD_NAMES

    if isinstance(value, Mapping):
        return any(_field_name(key) in _STATUS_FIELD_NAMES for key in value)

    if isinstance(value, Iterable):
        return any(_contains_status_field(item) for item in value)

    return False


def _new_status(payloads: list[Mapping[str, Any]]) -> str | None:
    explicit = _first_string(
        payloads,
        (
            "newStatus",
            "new_status",
            "toStatus",
            "to_status",
            "statusName",
            "stateName",
            "workflowStateName",
        ),
    )
    if explicit:
        return explicit

    for payload in payloads:
        changes = payload.get("changes")
        changed_status = _status_from_changes(changes)
        if changed_status:
            return changed_status

    for payload in payloads:
        for key in ("state", "workflowState", "status"):
            value = payload.get(key)
            status = _status_name(value)
            if status:
                return status

    return None


def _status_from_changes(changes: Any) -> str | None:
    if not isinstance(changes, Mapping):
        return None

    for key, value in changes.items():
        if _field_name(key) not in _STATUS_FIELD_NAMES:
            continue

        if isinstance(value, Mapping):
            for status_key in ("newValue", "new", "to", "after", "name"):
                status = _status_name(value.get(status_key))
                if status:
                    return status
        else:
            status = _status_name(value)
            if status:
                return status

    return None


def _status_name(value: Any) -> str | None:
    if isinstance(value, str):
        return value

    if isinstance(value, Mapping):
        for key in ("name", "title", "value"):
            if isinstance(value.get(key), str):
                return value[key]

    return None


def _first_string(payloads: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    field_names = {_field_name(key) for key in keys}
    for payload in payloads:
        for key, value in payload.items():
            if _field_name(key) in field_names and isinstance(value, str) and value.strip():
                return value
    return None


def _has_prefix(title: str) -> bool:
    return _normalize(title).startswith(PREFIX.lower())


def _field_name(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def _normalize(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    spaced = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", value)
    normalized = re.sub(r"[_\-]+", " ", spaced).strip().lower()
    return re.sub(r"\s+", " ", normalized)


def main() -> int:
    """Read a JSON event from stdin and print the computed action, if any."""

    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
