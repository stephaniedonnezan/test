"""Build Linear issue-title updates for research status changes.

The automation receives Linear webhook data in a few shapes depending on the
trigger source.  This module keeps the decision pure: callers pass the event
payload and receive an update action when the issue moved to "to research".
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_CHANGE_CONTAINER_KEYS = {
    "changes",
    "previousvalues",
    "previousvalue",
    "updatedfrom",
    "updatedfromvalues",
}
_FIELD_LIST_KEYS = {
    "updatedfields",
    "changedfields",
    "changedfieldnames",
}
_ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "key", "id")
_NEW_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "statusName",
    "status_name",
    "stateName",
    "state_name",
    "workflowStateName",
    "workflow_state_name",
)
_STATUS_VALUE_KEYS = ("status", "state", "workflowState", "workflow_state")
_TRIGGER_KEYS = ("trigger", "webhookType", "action", "type", "event", "eventType")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to research.

    The returned shape is intentionally small so an automation runner can map it
    to the Linear API call it uses:

    ``{"action": "update_issue_title", "issueId": "...", "title": "..."}``
    """

    if not isinstance(event, Mapping):
        return None

    mappings = list(_walk_mappings(event))
    if not _is_status_change_event(mappings):
        return None

    new_status = _extract_new_status(mappings)
    if _normalize_text(new_status) != TARGET_STATUS:
        return None

    title_context = _first_mapping_with_text(mappings, "title")
    title = _text_value(title_context.get("title")) if title_context else None
    if not title:
        return None
    if title.lower().startswith(PREFIX.lower()):
        return None

    issue_id = _extract_issue_id(mappings, title_context)
    if not issue_id:
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _is_status_change_event(mappings: list[Mapping[str, Any]]) -> bool:
    trigger_values = [
        value
        for mapping in mappings
        for key in _TRIGGER_KEYS
        if (value := _text_value(mapping.get(key)))
    ]
    normalized_triggers = [_normalize_text(value) for value in trigger_values]

    if any(_looks_like_direct_status_change(value) for value in normalized_triggers):
        return True

    if not any(_looks_like_issue_update(value) for value in normalized_triggers):
        return False

    return _has_status_change_metadata(mappings)


def _looks_like_direct_status_change(value: str) -> bool:
    words = set(value.split())
    return (
        ("status" in words and {"change", "changed"} & words)
        or ("state" in words and {"change", "changed"} & words)
        or ("workflow" in words and "state" in words and {"change", "changed"} & words)
    )


def _looks_like_issue_update(value: str) -> bool:
    words = set(value.split())
    return bool({"update", "updated"} & words)


def _has_status_change_metadata(mappings: list[Mapping[str, Any]]) -> bool:
    for mapping in mappings:
        for key, value in mapping.items():
            normalized_key = _normalize_key(key)
            if normalized_key in _FIELD_LIST_KEYS and _contains_status_field(value):
                return True
            if normalized_key in _CHANGE_CONTAINER_KEYS and _contains_status_field(value):
                return True
            if normalized_key in {"field", "name"} and _is_status_field_name(value):
                return True
    return False


def _extract_new_status(mappings: list[Mapping[str, Any]]) -> str | None:
    for key in _NEW_STATUS_KEYS:
        for mapping in mappings:
            value = _text_value(mapping.get(key))
            if value:
                return value

    for mapping in mappings:
        for key, value in mapping.items():
            if _normalize_key(key) in _CHANGE_CONTAINER_KEYS:
                changed_status = _extract_status_from_change_container(value)
                if changed_status:
                    return changed_status

    for key in _STATUS_VALUE_KEYS:
        for mapping in mappings:
            value = _status_value(mapping.get(key))
            if value:
                return value

    return None


def _extract_status_from_change_container(value: Any) -> str | None:
    if isinstance(value, Mapping):
        field_name = _text_value(value.get("field")) or _text_value(value.get("name"))
        if field_name and _is_status_field_name(field_name):
            changed_status = _changed_value(value)
            if changed_status:
                return changed_status

        for key, item in value.items():
            if _is_status_field_name(key):
                changed_status = _changed_value(item)
                if changed_status:
                    return changed_status
        for item in value.values():
            changed_status = _extract_status_from_change_container(item)
            if changed_status:
                return changed_status

    if isinstance(value, list):
        for item in value:
            changed_status = _extract_status_from_change_container(item)
            if changed_status:
                return changed_status

    return None


def _changed_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("newValue", "new_value", "new", "to", "after", "current", "name"):
            text = _status_value(value.get(key))
            if text:
                return text
    return _status_value(value)


def _extract_issue_id(
    mappings: list[Mapping[str, Any]], title_context: Mapping[str, Any] | None
) -> str | None:
    if title_context:
        issue_id = _first_text_for_keys([title_context], _ISSUE_ID_KEYS)
        if issue_id:
            return issue_id

    return _first_text_for_keys(mappings, _ISSUE_ID_KEYS)


def _first_mapping_with_text(
    mappings: Iterable[Mapping[str, Any]], key: str
) -> Mapping[str, Any] | None:
    for mapping in mappings:
        if _text_value(mapping.get(key)):
            return mapping
    return None


def _first_text_for_keys(
    mappings: Iterable[Mapping[str, Any]], keys: Iterable[str]
) -> str | None:
    for key in keys:
        for mapping in mappings:
            value = _text_value(mapping.get(key))
            if value:
                return value
    return None


def _contains_status_field(value: Any) -> bool:
    if _is_status_field_name(value):
        return True

    if isinstance(value, Mapping):
        return any(
            _is_status_field_name(key) or _contains_status_field(item)
            for key, item in value.items()
        )

    if isinstance(value, list):
        return any(_contains_status_field(item) for item in value)

    return False


def _is_status_field_name(value: Any) -> bool:
    key = _normalize_key(value)
    return (
        key == "status"
        or key == "statusid"
        or key == "state"
        or key == "stateid"
        or key == "workflowstate"
        or key == "workflowstateid"
        or key.endswith("status")
        or key.endswith("statusid")
    )


def _status_value(value: Any) -> str | None:
    text = _text_value(value)
    if text:
        return text
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            text = _text_value(value.get(key))
            if text:
                return text
    return None


def _text_value(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _walk_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for item in value.values():
            yield from _walk_mappings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_mappings(item)


def _normalize_text(value: Any) -> str:
    text = str(value or "")
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[_\-]+", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def _normalize_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
