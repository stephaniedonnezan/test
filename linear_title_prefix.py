"""Build Linear issue title updates for Cursor research status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_PREFIX_RE = re.compile(r"^\s*cursor\s+researching\b\s*:?\s*", re.IGNORECASE)
_CAMEL_BOUNDARY_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_WORD_SEPARATOR_RE = re.compile(r"[^a-z0-9]+")

_DIRECT_STATUS_CHANGE_VALUES = {"status changed", "status change"}
_ISSUE_UPDATE_VALUES = {"update", "updated", "issue update", "issue updated", "updated issue"}
_STATUS_FIELD_NAMES = {
    "state",
    "stateid",
    "state_id",
    "status",
    "statusid",
    "status_id",
    "workflowstate",
    "workflowstateid",
    "workflow_state",
    "workflow_state_id",
}
_EXPLICIT_STATUS_KEYS = ("newStatus", "new_status", "newState", "new_state")
_STATUS_FALLBACK_KEYS = ("status", "state", "workflowState", "workflow_state")
_ISSUE_ID_KEYS = ("issueId", "issue_id", "id", "identifier")
_TITLE_KEYS = ("title", "issueTitle", "issue_title")
_TRIGGER_KEYS = ("trigger", "webhookType", "webhook_type")
_ISSUE_UPDATE_KEYS = ("action", "type", "webhookType", "webhook_type", "trigger")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to To Research.

    The automation runner consumes the returned action and performs the Linear
    mutation. Non-matching events return ``None`` so callers can no-op safely.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    status = _extract_new_status(event)
    if _normalize_phrase(status) != TARGET_STATUS:
        return None

    title = _extract_text(event, _TITLE_KEYS)
    issue_id = _extract_text(event, _ISSUE_ID_KEYS)
    if not title or not issue_id:
        return None

    stripped_title = title.strip()
    if _PREFIX_RE.match(stripped_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {stripped_title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    for key in _TRIGGER_KEYS:
        for value in _values_for_key(event, key):
            if _normalize_phrase(value) in _DIRECT_STATUS_CHANGE_VALUES:
                return True

    if not _updated_fields_include_status(event):
        return False

    for key in _ISSUE_UPDATE_KEYS:
        for value in _values_for_key(event, key):
            if _normalize_phrase(value) in _ISSUE_UPDATE_VALUES:
                return True

    return False


def _updated_fields_include_status(event: Mapping[str, Any]) -> bool:
    for value in _values_for_key(event, "updatedFields"):
        if _contains_status_field_name(value):
            return True

    for value in _values_for_key(event, "updated_fields"):
        if _contains_status_field_name(value):
            return True

    for value in _values_for_key(event, "updatedFrom"):
        if isinstance(value, Mapping) and any(_is_status_field_name(key) for key in value):
            return True
        if _contains_status_field_name(value):
            return True

    for value in _values_for_key(event, "updated_from"):
        if isinstance(value, Mapping) and any(_is_status_field_name(key) for key in value):
            return True
        if _contains_status_field_name(value):
            return True

    return False


def _contains_status_field_name(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field_name(value)

    if isinstance(value, Mapping):
        return any(_is_status_field_name(key) or _contains_status_field_name(item) for key, item in value.items())

    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        return any(_contains_status_field_name(item) for item in value)

    return False


def _is_status_field_name(value: Any) -> bool:
    if not isinstance(value, str):
        return False

    normalized = _normalize_key(value)
    return normalized in _STATUS_FIELD_NAMES


def _extract_new_status(event: Mapping[str, Any]) -> str | None:
    for key in _EXPLICIT_STATUS_KEYS:
        text = _extract_status_text(event, key)
        if text:
            return text

    for key in _STATUS_FALLBACK_KEYS:
        text = _extract_status_text(event, key)
        if text:
            return text

    return None


def _extract_status_text(event: Mapping[str, Any], key: str) -> str | None:
    for value in _values_for_key(event, key):
        if isinstance(value, str) and value.strip():
            return value

        if isinstance(value, Mapping):
            name = value.get("name")
            if isinstance(name, str) and name.strip():
                return name

    return None


def _extract_text(event: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        for value in _values_for_key(event, key):
            if isinstance(value, str) and value.strip():
                return value

    return None


def _values_for_key(value: Any, wanted_key: str) -> Iterable[Any]:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if key == wanted_key:
                yield item
            yield from _values_for_key(item, wanted_key)
    elif isinstance(value, list):
        for item in value:
            yield from _values_for_key(item, wanted_key)


def _normalize_phrase(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    with_spaces = _CAMEL_BOUNDARY_RE.sub(" ", value.strip())
    return _WORD_SEPARATOR_RE.sub(" ", with_spaces.lower()).strip()


def _normalize_key(value: str) -> str:
    with_spaces = _CAMEL_BOUNDARY_RE.sub(" ", value.strip())
    return _WORD_SEPARATOR_RE.sub("", with_spaces.lower()).strip()


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
