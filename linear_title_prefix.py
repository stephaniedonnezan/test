"""Build title updates for Linear issues entering research.

The automation runner can pass either a flat Cursor trigger payload or a nested
Linear webhook payload. This module keeps the side effect separate by returning
an action dictionary for the caller to apply.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"

_CAMEL_CASE_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_NON_ALNUM = re.compile(r"[^a-z0-9]+")
_PREFIX_PATTERN = re.compile(r"^\s*cursor researching\b", re.IGNORECASE)

_NESTED_MAPPING_KEYS = (
    "triggerContext",
    "data",
    "issue",
    "node",
    "payload",
    "resource",
)
_ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "key")
_GENERIC_ID_KEYS = ("id",)
_TITLE_KEYS = ("title",)
_EXPLICIT_NEW_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "toStatus",
    "to_status",
    "statusName",
    "stateName",
)
_STATUS_FALLBACK_KEYS = (
    "status",
    "state",
    "workflowState",
    "workflow_state",
)
_TRIGGER_KEYS = ("trigger", "action", "type", "webhookType", "eventType")
_UPDATED_FIELD_KEYS = ("updatedFields", "updated_fields", "changedFields", "changed_fields")
_CHANGE_RECORD_KEYS = ("changes", "changed")
_UPDATED_FROM_KEYS = ("updatedFrom", "updated_from")


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to to-research."""
    if not isinstance(event, Mapping):
        return None

    candidates = _candidate_mappings(event)
    if not _is_status_change_event(candidates):
        return None

    new_status = _extract_new_status(candidates)
    if _normalize_text(new_status) != TARGET_STATUS:
        return None

    title = _first_text_value(candidates, _TITLE_KEYS)
    issue_id = _first_text_value(candidates, _ISSUE_ID_KEYS)
    if issue_id is None:
        issue_id = _first_text_value(candidates, _GENERIC_ID_KEYS)

    if title is None or issue_id is None:
        return None

    title = title.strip()
    issue_id = issue_id.strip()
    if not title or not issue_id or _PREFIX_PATTERN.match(title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _candidate_mappings(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return likely payload maps ordered from most issue-specific to broadest."""
    candidates: list[Mapping[str, Any]] = []
    seen: set[int] = set()

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and id(value) not in seen:
            candidates.append(value)
            seen.add(id(value))

    trigger_context = event.get("triggerContext")
    add(trigger_context)

    data = event.get("data")
    if isinstance(data, Mapping):
        add(data.get("issue"))
        add(data)

    add(event.get("issue"))
    add(event)

    for mapping in list(candidates):
        for key in _NESTED_MAPPING_KEYS:
            add(mapping.get(key))

    return candidates


def _is_status_change_event(candidates: Iterable[Mapping[str, Any]]) -> bool:
    for mapping in candidates:
        for key in _TRIGGER_KEYS:
            if _is_direct_status_change_trigger(mapping.get(key)):
                return True

        if _has_updated_status_field(mapping):
            return True

        if any(_text_from_value(mapping.get(key)) is not None for key in _EXPLICIT_NEW_STATUS_KEYS):
            return True

    return False


def _is_direct_status_change_trigger(value: Any) -> bool:
    normalized = _normalize_text(value)
    return normalized in {
        "status changed",
        "state changed",
        "workflow state changed",
        "workflow status changed",
    }


def _has_updated_status_field(mapping: Mapping[str, Any]) -> bool:
    for key in _UPDATED_FIELD_KEYS:
        if _contains_status_field(mapping.get(key)):
            return True

    for key in _CHANGE_RECORD_KEYS:
        changes = mapping.get(key)
        if isinstance(changes, Mapping):
            if any(_is_status_field(field) for field in changes):
                return True
        elif _contains_status_field(changes):
            return True

    for key in _UPDATED_FROM_KEYS:
        updated_from = mapping.get(key)
        if isinstance(updated_from, Mapping) and any(_is_status_field(field) for field in updated_from):
            return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)

    if isinstance(value, Mapping):
        field = (
            value.get("field")
            or value.get("fieldName")
            or value.get("field_name")
            or value.get("name")
            or value.get("key")
        )
        if _is_status_field(field):
            return True
        return any(_contains_status_field(item) for item in value.values())

    if isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray, str)):
        return any(_contains_status_field(item) for item in value)

    return False


def _is_status_field(value: Any) -> bool:
    normalized = _normalize_text(value)
    return normalized in {
        "status",
        "status id",
        "state",
        "state id",
        "workflow state",
        "workflow state id",
        "workflow status",
        "workflow status id",
    }


def _extract_new_status(candidates: Iterable[Mapping[str, Any]]) -> str | None:
    candidate_list = list(candidates)

    for mapping in candidate_list:
        for key in _EXPLICIT_NEW_STATUS_KEYS:
            text = _text_from_value(mapping.get(key))
            if text:
                return text

    for mapping in candidate_list:
        status = _extract_status_from_changes(mapping)
        if status:
            return status

    for mapping in candidate_list:
        for key in _STATUS_FALLBACK_KEYS:
            text = _text_from_value(mapping.get(key))
            if text:
                return text

    return None


def _extract_status_from_changes(mapping: Mapping[str, Any]) -> str | None:
    for key in _CHANGE_RECORD_KEYS:
        changes = mapping.get(key)
        if isinstance(changes, Mapping):
            for field, record in changes.items():
                if _is_status_field(field):
                    status = _extract_new_value(record)
                    if status:
                        return status
        elif isinstance(changes, Iterable) and not isinstance(changes, (bytes, bytearray, str)):
            for record in changes:
                if isinstance(record, Mapping) and _contains_status_field(record):
                    status = _extract_new_value(record)
                    if status:
                        return status

    return None


def _extract_new_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in (
            "newValue",
            "new_value",
            "to",
            "after",
            "new",
            "currentValue",
            "current_value",
            "value",
            "name",
        ):
            text = _text_from_value(value.get(key))
            if text:
                return text
    return _text_from_value(value)


def _first_text_value(candidates: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for mapping in candidates:
        for key in keys:
            text = _text_from_value(mapping.get(key))
            if text:
                return text
    return None


def _text_from_value(value: Any) -> str | None:
    if value is None:
        return None

    if isinstance(value, Mapping):
        for key in ("name", "title", "identifier", "key", "id"):
            text = _text_from_value(value.get(key))
            if text:
                return text
        return None

    text = str(value).strip()
    return text or None


def _normalize_text(value: Any) -> str:
    text = _text_from_value(value)
    if text is None:
        return ""
    text = _CAMEL_CASE_BOUNDARY.sub(" ", text)
    text = _NON_ALNUM.sub(" ", text.lower())
    return " ".join(text.split())


def main() -> int:
    event = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(event), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
