"""Helpers for prefixing Linear issue titles during research handoff."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow state"}
_STATUS_VALUE_KEYS = (
    "newStatus",
    "new_status",
    "toStatus",
    "to_status",
    "statusName",
    "status_name",
    "stateName",
    "state_name",
    "workflowStateName",
    "workflow_state_name",
)
_TRIGGER_KEYS = ("trigger", "event", "eventType", "webhookType", "action", "type")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Build a title update action for Linear issues moved to research.

    The automation runtime is responsible for applying the returned action.
    Returning ``None`` means the event should be ignored.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    new_status = _find_new_status(event)
    if _normalize(new_status) != TARGET_STATUS:
        return None

    title = _find_first_string(event, ("title",))
    if not title:
        return None

    stripped_title = title.strip()
    if _has_research_prefix(stripped_title):
        return None

    issue_id = _find_first_string(
        event,
        ("issueId", "issue_id", "identifier", "key", "id"),
    )
    if not issue_id:
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {stripped_title}",
    }


def _candidate_payloads(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    payloads: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in payloads:
            payloads.append(value)

    trigger_context = event.get("triggerContext")
    add(trigger_context)
    if isinstance(trigger_context, Mapping):
        trigger_data = trigger_context.get("data")
        if isinstance(trigger_data, Mapping):
            add(trigger_data.get("issue"))
            add(trigger_data)
        add(trigger_context.get("issue"))

    data = event.get("data")
    if isinstance(data, Mapping):
        add(data.get("issue"))
        add(data)

    add(event.get("issue"))
    add(event)

    return payloads


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    for payload in _candidate_payloads(event):
        for key in _TRIGGER_KEYS:
            trigger_value = payload.get(key)
            if _looks_like_status_change(trigger_value):
                return True
            if _looks_like_update_event(trigger_value):
                return _updated_fields_include_status(event)

    return False


def _looks_like_status_change(value: Any) -> bool:
    normalized = _normalize(value)
    if normalized in {
        "status changed",
        "status change",
        "status updated",
        "state changed",
        "state updated",
        "workflow state changed",
        "workflow state updated",
    }:
        return True

    words = set(normalized.split())
    return bool(
        words & {"status", "state", "workflow"}
        and words & {"changed", "change", "updated", "update", "moved", "move"}
    )


def _looks_like_update_event(value: Any) -> bool:
    normalized = _normalize(value)
    return normalized in {"update", "updated", "issue update", "issue updated", "updated issue"}


def _updated_fields_include_status(event: Mapping[str, Any]) -> bool:
    for payload in _candidate_payloads(event):
        if _status_fields_contain_status(payload.get("updatedFields")):
            return True
        if _status_fields_contain_status(payload.get("updated_fields")):
            return True
        if _changes_include_status(payload.get("changes")):
            return True
        if _changes_include_status(payload.get("updatedFrom")):
            return True
        if _changes_include_status(payload.get("updated_from")):
            return True

    return False


def _status_fields_contain_status(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_field_name(value) in _STATUS_FIELD_NAMES

    if isinstance(value, Mapping):
        return any(_normalize_field_name(key) in _STATUS_FIELD_NAMES for key in value)

    if isinstance(value, Iterable):
        for item in value:
            if isinstance(item, Mapping):
                field = item.get("name") or item.get("field") or item.get("key")
                if _normalize_field_name(field) in _STATUS_FIELD_NAMES:
                    return True
            elif _normalize_field_name(item) in _STATUS_FIELD_NAMES:
                return True

    return False


def _changes_include_status(value: Any) -> bool:
    if not isinstance(value, Mapping):
        return False

    for key in value:
        normalized = _normalize_field_name(key)
        if normalized in _STATUS_FIELD_NAMES or normalized.endswith("statusid") or normalized.endswith("stateid"):
            return True

    return False


def _find_new_status(event: Mapping[str, Any]) -> str | None:
    for status in _statuses_from_changes(event):
        if status:
            return status

    for payload in _candidate_payloads(event):
        for key in _STATUS_VALUE_KEYS:
            status = _string_value(payload.get(key))
            if status:
                return status

    for payload in _candidate_payloads(event):
        for key in ("status", "state", "workflowState", "workflow_state"):
            status = _string_value(payload.get(key))
            if status:
                return status

    return None


def _statuses_from_changes(event: Mapping[str, Any]) -> Iterable[str | None]:
    for payload in _candidate_payloads(event):
        changes = payload.get("changes")
        if isinstance(changes, Mapping):
            for key in ("status", "state", "workflowState", "workflow_state"):
                yield _status_from_change(changes.get(key))

        updated_fields = payload.get("updatedFields") or payload.get("updated_fields")
        if isinstance(updated_fields, Iterable) and not isinstance(updated_fields, (str, bytes)):
            for item in updated_fields:
                if not isinstance(item, Mapping):
                    continue
                field = item.get("name") or item.get("field") or item.get("key")
                if _normalize_field_name(field) in _STATUS_FIELD_NAMES:
                    yield _status_from_change(item)


def _status_from_change(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("newValue", "new_value", "to", "after", "name"):
            status = _string_value(value.get(key))
            if status:
                return status
    return _string_value(value)


def _find_first_string(event: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for payload in _candidate_payloads(event):
        for key in keys:
            value = _string_value(payload.get(key))
            if value:
                return value

    return None


def _string_value(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "identifier", "key", "id"):
            string = _string_value(value.get(key))
            if string:
                return string

    return None


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())


def _normalize(value: Any) -> str:
    text = _string_value(value) or ""
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.casefold().split())


def _normalize_field_name(value: Any) -> str:
    return _normalize(value).replace(" ", "")


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    print(json.dumps(update, indent=2, sort_keys=True) if update else "null")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
