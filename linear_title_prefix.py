"""Build Linear issue title updates for issues entering To Research.

The module is intentionally small and dependency-free so it can be used by a
Cursor automation step or invoked directly with a JSON payload on stdin.
"""

from __future__ import annotations

import json
import re
import sys
from collections import deque
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_TRIGGER_KEYS = {"trigger", "webhooktype", "webhook type", "action", "type", "event", "eventtype", "event type"}
_DIRECT_STATUS_CHANGE_EVENTS = {
    "status changed",
    "status change",
    "status updated",
    "status update",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
}
_GENERIC_UPDATE_EVENTS = {"update", "updated", "issue update", "issue updated", "updated issue"}
_STATUS_KEYS = {"status", "state", "workflowstate", "workflow state", "workflow_state"}
_NEW_STATUS_KEYS = {
    "newstatus",
    "new status",
    "new_status",
    "newstate",
    "new state",
    "new_state",
    "newworkflowstate",
    "new workflow state",
    "new_workflow_state",
    "statusname",
    "status name",
    "status_name",
    "statename",
    "state name",
    "state_name",
}
_UPDATED_FIELD_KEYS = {
    "updatedfields",
    "updated fields",
    "updated_fields",
    "changedfields",
    "changed fields",
    "changed_fields",
    "changedfieldnames",
    "changed field names",
    "changed_field_names",
}
_CHANGE_CONTAINER_KEYS = {
    "changes",
    "changed",
    "updatedfrom",
    "updated from",
    "updated_from",
    "previousvalues",
    "previous values",
    "previous_values",
}
_ID_KEYS = ("issueid", "issue id", "issue_id", "identifier", "key", "id")
_TITLE_KEYS = ("title",)


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return an issue title update action when an issue moves to To Research.

    The function accepts both the flat Cursor automation trigger context and
    common nested Linear webhook shapes. It returns ``None`` for payloads that
    are not status changes, do not target To Research, lack issue metadata, or
    already have the desired prefix.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    status = _extract_status(event)
    if _normalize(status) != TARGET_STATUS:
        return None

    issue_id = _extract_issue_id(event)
    title = _extract_title(event)
    if not issue_id or not title:
        return None

    cleaned_title = title.strip()
    if _has_prefix(cleaned_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {cleaned_title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    trigger_values = {_normalize(value) for value in _values_for_normalized_keys(event, _TRIGGER_KEYS)}

    if trigger_values & _DIRECT_STATUS_CHANGE_EVENTS:
        return True

    if trigger_values & _GENERIC_UPDATE_EVENTS:
        return _status_marked_changed(event)

    return _status_marked_changed(event) and bool(_extract_status(event))


def _extract_status(event: Mapping[str, Any]) -> str | None:
    explicit = _first_text_for_keys(event, _NEW_STATUS_KEYS)
    if explicit:
        return explicit

    return _first_text_for_keys(event, _STATUS_KEYS)


def _extract_issue_id(event: Mapping[str, Any]) -> str | None:
    for candidate in _issue_like_maps(event):
        issue_id = _first_direct_text_for_keys(candidate, _ID_KEYS)
        if issue_id:
            return issue_id

    return _first_text_for_keys(event, _ID_KEYS)


def _extract_title(event: Mapping[str, Any]) -> str | None:
    for candidate in _issue_like_maps(event):
        title = _first_direct_text_for_keys(candidate, _TITLE_KEYS)
        if title:
            return title

    return _first_text_for_keys(event, _TITLE_KEYS)


def _issue_like_maps(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    candidates = list(_walk_mappings(event))
    return sorted(candidates, key=lambda item: 0 if _first_direct_text_for_keys(item, _TITLE_KEYS) else 1)


def _status_marked_changed(value: Any) -> bool:
    queue: deque[tuple[Any, str | None]] = deque([(value, None)])

    while queue:
        current, parent_key = queue.popleft()

        if isinstance(current, Mapping):
            for key, child in current.items():
                normalized_key = _normalize_key(key)
                if normalized_key in _UPDATED_FIELD_KEYS and _contains_status_field_reference(child):
                    return True
                if normalized_key in _CHANGE_CONTAINER_KEYS and _contains_status_key(child):
                    return True
                if parent_key in _CHANGE_CONTAINER_KEYS and normalized_key in _STATUS_KEYS:
                    return True
                queue.append((child, normalized_key))
        elif isinstance(current, list):
            queue.extend((item, parent_key) for item in current)

    return False


def _contains_status_field_reference(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_key(value) in _STATUS_KEYS

    if isinstance(value, Mapping):
        return any(_normalize_key(key) in _STATUS_KEYS or _contains_status_field_reference(child) for key, child in value.items())

    if isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray, str)):
        return any(_contains_status_field_reference(item) for item in value)

    return False


def _contains_status_key(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(_normalize_key(key) in _STATUS_KEYS or _contains_status_key(child) for key, child in value.items())

    if isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray, str)):
        return any(_contains_status_key(item) for item in value)

    return False


def _first_text_for_keys(value: Any, keys: Iterable[str]) -> str | None:
    normalized_keys = {_normalize_key(key) for key in keys}

    for mapping in _walk_mappings(value):
        result = _first_direct_text_for_keys(mapping, normalized_keys)
        if result:
            return result

    return None


def _first_direct_text_for_keys(mapping: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    normalized_keys = {_normalize_key(key) for key in keys}

    for key, value in mapping.items():
        if _normalize_key(key) in normalized_keys:
            text = _coerce_text(value)
            if text:
                return text

    return None


def _values_for_normalized_keys(value: Any, keys: Iterable[str]) -> list[Any]:
    normalized_keys = {_normalize_key(key) for key in keys}
    values: list[Any] = []

    for mapping in _walk_mappings(value):
        values.extend(child for key, child in mapping.items() if _normalize_key(key) in normalized_keys)

    return values


def _walk_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    queue: deque[Any] = deque([value])

    while queue:
        current = queue.popleft()

        if isinstance(current, Mapping):
            yield current
            queue.extend(current.values())
        elif isinstance(current, list):
            queue.extend(current)


def _coerce_text(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "identifier", "key", "id"):
            text = _first_direct_text_for_keys(value, (key,))
            if text:
                return text

    return None


def _has_prefix(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())


def _normalize(value: Any) -> str:
    text = _coerce_text(value)
    if not text:
        return ""

    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[_\-.]+", " ", text)
    text = re.sub(r"[^0-9A-Za-z]+", " ", text)
    return " ".join(text.casefold().split())


def _normalize_key(value: Any) -> str:
    return _normalize(str(value))


def main() -> int:
    payload = json.load(sys.stdin)
    update = build_issue_title_update(payload)
    if update is not None:
        json.dump(update, sys.stdout)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
