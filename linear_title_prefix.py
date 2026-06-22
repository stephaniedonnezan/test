"""Build Linear issue-title updates for Cursor research automations."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


RESEARCH_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELDS = {
    "newStatus",
    "new_status",
    "status",
    "state",
    "workflowState",
}
_STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow_state"}
_UPDATE_EVENT_NAMES = {"update", "updated", "issue update", "issue updated", "updated issue"}
_DIRECT_STATUS_EVENT_NAMES = {
    "status changed",
    "status change",
    "status updated",
    "state changed",
    "workflow state changed",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to To Research.

    The automation payloads have varied between flat Cursor trigger contexts and
    nested Linear webhook events, so this function accepts either shape and
    returns a small, runtime-agnostic action dictionary.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    status = _extract_new_status(event)
    if _normalize_label(status) != TARGET_STATUS:
        return None

    issue_id = _extract_issue_id(event)
    title = _extract_title(event)
    if not issue_id or not title:
        return None

    if _has_research_prefix(title):
        new_title = title
    else:
        new_title = f"{RESEARCH_PREFIX}: {title}"

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": new_title,
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    event_names = {
        _normalize_event_name(value)
        for value in _event_name_values(event)
        if _normalize_event_name(value)
    }

    if event_names & _DIRECT_STATUS_EVENT_NAMES:
        return True

    if event_names & _UPDATE_EVENT_NAMES:
        return _updated_fields_include_status(event) or _changes_include_status(event)

    return False


def _event_name_values(event: Mapping[str, Any]) -> list[Any]:
    values: list[Any] = []
    for context in _contexts(event):
        for key in ("trigger", "webhookType", "action", "type"):
            if key in context:
                values.append(context[key])
    return values


def _updated_fields_include_status(event: Mapping[str, Any]) -> bool:
    for context in _contexts(event):
        for key in ("updatedFields", "changedFields"):
            fields = context.get(key)
            if isinstance(fields, str):
                fields = [fields]
            if isinstance(fields, list):
                normalized_fields = {_normalize_field_name(field) for field in fields}
                if normalized_fields & _STATUS_FIELD_NAMES:
                    return True
    return False


def _changes_include_status(event: Mapping[str, Any]) -> bool:
    for context in _contexts(event):
        changes = context.get("changes") or context.get("updatedFrom")
        if isinstance(changes, Mapping):
            for key in changes:
                normalized_key = _normalize_field_name(key)
                if normalized_key in _STATUS_FIELD_NAMES or normalized_key in {"stateid", "workflowstateid"}:
                    return True
    return False


def _extract_new_status(event: Mapping[str, Any]) -> str | None:
    for context in _contexts(event):
        for key in ("newStatus", "new_status"):
            status = _status_value(context.get(key))
            if status:
                return status

    status_from_changes = _status_from_changes(event)
    if status_from_changes:
        return status_from_changes

    for context in _contexts(event):
        for key in ("status", "state", "workflowState"):
            status = _status_value(context.get(key))
            if status:
                return status

    return None


def _status_from_changes(event: Mapping[str, Any]) -> str | None:
    for context in _contexts(event):
        changes = context.get("changes")
        if not isinstance(changes, Mapping):
            continue
        for key in _STATUS_FIELDS:
            status = _status_value(changes.get(key))
            if status:
                return status
    return None


def _status_value(value: Any) -> str | None:
    if isinstance(value, str):
        value = value.strip()
        return value or None

    if isinstance(value, Mapping):
        for key in ("to", "new", "after", "name", "title"):
            status = _status_value(value.get(key))
            if status:
                return status

    return None


def _extract_issue_id(event: Mapping[str, Any]) -> str | None:
    for key in ("identifier", "key", "issueId", "issue_id"):
        value = _first_string_for_key(event, key)
        if value:
            return value
    return _first_string_for_key(event, "id")


def _extract_title(event: Mapping[str, Any]) -> str | None:
    return _first_string_for_key(event, "title")


def _first_string_for_key(event: Mapping[str, Any], key: str) -> str | None:
    for context in _contexts(event):
        value = context.get(key)
        if isinstance(value, str):
            value = value.strip()
            if value:
                return value
    return None


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []
    seen: set[int] = set()

    def add_context(value: Any) -> None:
        if not isinstance(value, Mapping) or id(value) in seen:
            return

        seen.add(id(value))
        contexts.append(value)

        for key in ("automation_trigger_info", "triggerContext", "data", "issue"):
            add_context(value.get(key))

    add_context(event)
    return contexts


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(RESEARCH_PREFIX.lower())


def _normalize_event_name(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    value = _split_camel_case(value)
    value = re.sub(r"[^a-zA-Z0-9]+", " ", value).strip().lower()
    return re.sub(r"\s+", " ", value)


def _normalize_label(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    value = _split_camel_case(value)
    value = re.sub(r"[^a-zA-Z0-9]+", " ", value).strip().lower()
    return re.sub(r"\s+", " ", value)


def _normalize_field_name(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^a-zA-Z0-9]+", "", value).lower()


def _split_camel_case(value: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)


def main() -> int:
    """Read a JSON event from stdin and print the update action, if any."""

    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
