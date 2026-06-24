"""Build Linear issue title updates for research status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow state"}
_DIRECT_STATUS_TRIGGERS = {
    "status changed",
    "status change",
    "status updated",
    "status update",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
}
_UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Any) -> dict[str, str] | None:
    """Return a Linear title update action when an issue enters research.

    The function accepts both the flat Cursor automation trigger context and
    nested Linear webhook-like payloads. It is side-effect free so callers can
    decide how to apply the returned action.
    """

    if not isinstance(event, Mapping):
        return None

    mappings = _candidate_mappings(event)
    if not _is_status_change_event(mappings):
        return None

    status = _first_text(mappings, ("newStatus", "new_status", "newState", "new_state"))
    if status is None:
        status = _status_from_changes(mappings)
    if status is None:
        status = _first_text(mappings, ("status", "state", "workflowState", "workflow_state"))

    if _normalize(status) != TARGET_STATUS:
        return None

    title = _first_text(mappings, ("title", "name", "summary"))
    issue_id = _first_text(mappings, ("issueId", "issue_id", "identifier", "key", "id"))
    if title is None or issue_id is None:
        return None

    title = title.strip()
    issue_id = issue_id.strip()
    if not title or not issue_id:
        return None
    if title.casefold().startswith(PREFIX.casefold()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _candidate_mappings(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    mappings: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in mappings:
            mappings.append(value)

    trigger_context = event.get("triggerContext")
    data = event.get("data")
    payload = event.get("payload")
    issue = event.get("issue")

    add(trigger_context)
    add(_get_mapping(trigger_context, "issue"))
    add(_get_mapping(trigger_context, "data"))
    add(_get_mapping(trigger_context, "data", "issue"))
    add(issue)
    add(data)
    add(_get_mapping(data, "issue"))
    add(payload)
    add(_get_mapping(payload, "issue"))
    add(event)
    return mappings


def _is_status_change_event(mappings: list[Mapping[str, Any]]) -> bool:
    trigger_values = []
    for mapping in mappings:
        for key in ("trigger", "webhookType", "action", "type"):
            value = mapping.get(key)
            if isinstance(value, str):
                trigger_values.append(_normalize(value))

    if any(value in _DIRECT_STATUS_TRIGGERS for value in trigger_values):
        return True

    fields_changed = _status_fields_changed(mappings)
    if any(value in _UPDATE_TRIGGERS for value in trigger_values):
        return fields_changed

    return fields_changed


def _status_fields_changed(mappings: list[Mapping[str, Any]]) -> bool:
    for mapping in mappings:
        updated_fields = mapping.get("updatedFields") or mapping.get("updated_fields")
        if _contains_status_field(updated_fields):
            return True

        changes = mapping.get("changes") or mapping.get("changedFields") or mapping.get("changed_fields")
        if isinstance(changes, Mapping) and _contains_status_field(changes.keys()):
            return True
        if _contains_status_field(changes):
            return True

    return False


def _status_from_changes(mappings: list[Mapping[str, Any]]) -> str | None:
    for mapping in mappings:
        changes = mapping.get("changes") or mapping.get("changedFields") or mapping.get("changed_fields")
        if not isinstance(changes, Mapping):
            continue

        for field_name, change in changes.items():
            if _normalize_field_name(field_name) not in _STATUS_FIELD_NAMES:
                continue

            text = _extract_changed_value(change)
            if text is not None:
                return text

    return None


def _extract_changed_value(change: Any) -> str | None:
    if isinstance(change, str):
        return change
    if isinstance(change, Mapping):
        for key in ("to", "new", "after", "newValue", "new_value", "name"):
            value = change.get(key)
            text = _text_value(value)
            if text is not None:
                return text
    return None


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_field_name(value) in _STATUS_FIELD_NAMES
    if isinstance(value, Mapping):
        return any(_normalize_field_name(key) in _STATUS_FIELD_NAMES for key in value.keys())
    if isinstance(value, list | tuple | set):
        return any(_contains_status_field(item) for item in value)
    return False


def _first_text(mappings: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for mapping in mappings:
        for key in keys:
            text = _text_value(mapping.get(key))
            if text is not None:
                return text
    return None


def _text_value(value: Any) -> str | None:
    if isinstance(value, str):
        text = value.strip()
        return text if text else None
    if isinstance(value, Mapping):
        for key in ("name", "title", "identifier", "id", "key"):
            text = _text_value(value.get(key))
            if text is not None:
                return text
    return None


def _get_mapping(value: Any, *keys: str) -> Mapping[str, Any] | None:
    current = value
    for key in keys:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current if isinstance(current, Mapping) else None


def _normalize(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().casefold()


def _normalize_field_name(value: Any) -> str:
    return _normalize(value).replace(" ", "")


def main() -> int:
    result = build_issue_title_update(json.load(sys.stdin))
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
