"""Build title update actions for Linear issues entering research.

The automation payloads this repository receives have varied over time:
some are flat Cursor trigger contexts and others resemble native Linear
webhook events.  This module keeps the behavior isolated in a pure function
so callers can decide how to apply the returned update action.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = frozenset({"status", "state", "workflowstate"})
DIRECT_STATUS_CHANGE_TRIGGERS = frozenset({"statuschanged", "statuschange"})
GENERIC_UPDATE_TRIGGERS = frozenset(
    {
        "update",
        "updated",
        "issueupdate",
        "issueupdated",
        "updatedissue",
    }
)


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return an issue-title update action when a status changes to research.

    The return value is intentionally data-only:

    ``{"action": "update_issue_title", "issueId": "...", "title": "..."}``

    If the event does not represent a status transition into ``to research``,
    or if it is missing a usable issue id/title, ``None`` is returned.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    status = _extract_new_status(event)
    if _normalize_status(status) != _normalize_status(TARGET_STATUS):
        return None

    issue = _extract_issue(event)
    issue_id = _clean_string(_first_string(issue, ("issueId", "issue_id", "identifier", "key", "id")))
    title = _clean_string(_first_string(issue, ("title", "name")))

    if not issue_id or not title:
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": _prefix_title(title),
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    trigger_values = {
        _normalize_key(value)
        for value in _values_for_keys(event, ("trigger", "webhookType", "action", "type"))
        if _clean_string(value)
    }

    if trigger_values & DIRECT_STATUS_CHANGE_TRIGGERS:
        return True

    if "statuschanged" in trigger_values or "statuschange" in trigger_values:
        return True

    if trigger_values & GENERIC_UPDATE_TRIGGERS:
        return _changed_status_fields(event)

    # Some Linear payloads expose no explicit update action but do include a
    # change record or updatedFrom entry for status/state.
    return _changed_status_fields(event)


def _extract_new_status(event: Mapping[str, Any]) -> str | None:
    for key in (
        "newStatus",
        "new_status",
        "statusName",
        "stateName",
        "workflowStateName",
        "toStatus",
        "to_state",
    ):
        value = _find_first_value(event, key)
        text = _status_text(value)
        if text:
            return text

    for container_key in ("changes", "updatedFields", "changedFields"):
        for value in _iter_named_containers(event, container_key):
            status = _status_from_change_container(value)
            if status:
                return status

    issue = _extract_issue(event)
    for key in ("status", "state", "workflowState"):
        status = _status_text(issue.get(key))
        if status:
            return status

    return None


def _extract_issue(event: Mapping[str, Any]) -> Mapping[str, Any]:
    merged = dict(event)

    for key in ("data", "payload", "triggerContext", "issue"):
        value = event.get(key)
        if isinstance(value, Mapping):
            merged.update(value)
            nested_issue = value.get("issue")
            if isinstance(nested_issue, Mapping):
                merged.update(nested_issue)

    return merged


def _changed_status_fields(event: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "changedFields"):
        for value in _iter_named_containers(event, key):
            if _container_mentions_status_field(value):
                return True

    for key in ("changes", "updatedFrom"):
        for value in _iter_named_containers(event, key):
            if _change_container_mentions_status(value):
                return True

    return False


def _container_mentions_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_key(value) in STATUS_FIELDS

    if isinstance(value, Mapping):
        field_name = _first_string(value, ("field", "fieldName", "name", "key"))
        if field_name and _normalize_key(field_name) in STATUS_FIELDS:
            return True
        return any(_container_mentions_status_field(item) for item in value.values())

    if _is_iterable_container(value):
        return any(_container_mentions_status_field(item) for item in value)

    return False


def _change_container_mentions_status(value: Any) -> bool:
    if isinstance(value, Mapping):
        if any(_normalize_key(key) in STATUS_FIELDS for key in value.keys()):
            return True
        field_name = _first_string(value, ("field", "fieldName", "name", "key"))
        if field_name and _normalize_key(field_name) in STATUS_FIELDS:
            return True
        return any(_change_container_mentions_status(item) for item in value.values())

    if _is_iterable_container(value):
        return any(_change_container_mentions_status(item) for item in value)

    return False


def _status_from_change_container(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("new", "to", "newValue", "toValue", "after", "current", "value"):
            status = _status_text(value.get(key))
            if status:
                return status

        for field in ("status", "state", "workflowState"):
            if field in value:
                status = _status_text(value[field])
                if status:
                    return status

        field_name = _first_string(value, ("field", "fieldName", "name", "key"))
        if field_name and _normalize_key(field_name) in STATUS_FIELDS:
            for key in ("new", "to", "newValue", "toValue", "after", "current", "value"):
                status = _status_text(value.get(key))
                if status:
                    return status

        for item in value.values():
            status = _status_from_change_container(item)
            if status:
                return status

    if _is_iterable_container(value):
        for item in value:
            status = _status_from_change_container(item)
            if status:
                return status

    return None


def _iter_named_containers(event: Mapping[str, Any], target_key: str) -> Iterable[Any]:
    for key, value in event.items():
        if key == target_key:
            yield value
        if isinstance(value, Mapping):
            yield from _iter_named_containers(value, target_key)
        elif _is_iterable_container(value):
            for item in value:
                if isinstance(item, Mapping):
                    yield from _iter_named_containers(item, target_key)


def _find_first_value(value: Any, target_key: str) -> Any:
    if isinstance(value, Mapping):
        if target_key in value:
            return value[target_key]
        for nested in value.values():
            found = _find_first_value(nested, target_key)
            if found is not None:
                return found
    elif _is_iterable_container(value):
        for item in value:
            found = _find_first_value(item, target_key)
            if found is not None:
                return found
    return None


def _values_for_keys(value: Any, keys: tuple[str, ...]) -> Iterable[Any]:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if key in keys:
                yield nested
            yield from _values_for_keys(nested, keys)
    elif _is_iterable_container(value):
        for item in value:
            yield from _values_for_keys(item, keys)


def _status_text(value: Any) -> str | None:
    if isinstance(value, str):
        return _clean_string(value)
    if isinstance(value, Mapping):
        return _clean_string(_first_string(value, ("name", "title", "label")))
    return None


def _first_string(source: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = source.get(key)
        if isinstance(value, str):
            return value
    return None


def _clean_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value or None


def _prefix_title(title: str) -> str:
    if title.lower().startswith(PREFIX.lower()):
        return title
    return f"{PREFIX}: {title}"


def _normalize_status(value: str | None) -> str | None:
    if value is None:
        return None
    return " ".join(_split_words(value))


def _normalize_key(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return "".join(_split_words(value))


def _split_words(value: str) -> list[str]:
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return [part.lower() for part in re.split(r"[^A-Za-z0-9]+", spaced) if part]


def _is_iterable_container(value: Any) -> bool:
    return isinstance(value, Iterable) and not isinstance(value, (str, bytes, bytearray, Mapping))


def main() -> int:
    """Read a JSON event from stdin and write the title update action."""

    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is None:
        return 0

    json.dump(update, sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
