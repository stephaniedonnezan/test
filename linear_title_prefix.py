"""Build Linear issue title updates for research status changes.

The automation runner can call ``build_issue_title_update`` with the Linear
webhook payload. When a status-change event moves an issue to "to research",
the function returns a small action object describing the title update.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow state"}
_DIRECT_STATUS_CHANGE_MARKERS = {
    "status changed",
    "status change",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
}
_GENERIC_UPDATE_MARKERS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}
_EXPLICIT_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newStatusName",
    "new_status_name",
    "newState",
    "new_state",
    "newWorkflowState",
    "new_workflow_state",
)
_STATUS_FALLBACK_KEYS = ("status", "state", "workflowState", "workflow_state")
_ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "key", "id")


def build_issue_title_update(event: Mapping[str, Any] | Any) -> dict[str, str] | None:
    """Return a title-update action when a Linear issue moves to research.

    The returned shape is intentionally small so the surrounding automation can
    translate it into the actual Linear API call:
    ``{"action": "update_issue_title", "issueId": "...", "title": "..."}``.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    if _normalize_words(_extract_status(event)) != TARGET_STATUS:
        return None

    title = _extract_string(event, ("title", "name"))
    issue_id = _extract_string(event, _ISSUE_ID_KEYS)
    if not title or not issue_id:
        return None

    title = title.strip()
    issue_id = issue_id.strip()
    if _already_prefixed(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    markers = {_normalize_words(value) for value in _event_marker_values(event)}
    if any(marker in _DIRECT_STATUS_CHANGE_MARKERS for marker in markers):
        return True

    if any(marker in _GENERIC_UPDATE_MARKERS for marker in markers):
        return _has_status_change_marker(event)

    return False


def _event_marker_values(value: Any) -> Iterable[Any]:
    marker_keys = {"trigger", "webhookType", "action", "type", "event", "eventType"}
    yield from _values_for_keys(value, marker_keys)


def _has_status_change_marker(event: Mapping[str, Any]) -> bool:
    for fields in _values_for_keys(
        event,
        {
            "updatedFields",
            "updated_fields",
            "changedFields",
            "changed_fields",
            "field",
            "fieldName",
            "field_name",
        },
    ):
        if _contains_status_field(fields):
            return True

    for changes in _values_for_keys(event, {"changes", "changed", "updates"}):
        if _changes_include_status(changes):
            return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_field_name(value) in _STATUS_FIELD_NAMES

    if isinstance(value, Mapping):
        field_value = _first_string(value, ("field", "fieldName", "field_name", "name", "key"))
        if field_value and _contains_status_field(field_value):
            return True
        return any(_contains_status_field(item) for item in value.values())

    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        return any(_contains_status_field(item) for item in value)

    return False


def _changes_include_status(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, nested_value in value.items():
            if _normalize_field_name(key) in _STATUS_FIELD_NAMES:
                return True
            if _changes_include_status(nested_value):
                return True
        return False

    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        return any(_changes_include_status(item) for item in value)

    return False


def _extract_status(event: Mapping[str, Any]) -> str | None:
    for key in _EXPLICIT_STATUS_KEYS:
        value = _extract_string(event, (key,))
        if value:
            return value

    for changes in _values_for_keys(event, {"changes", "changed", "updates"}):
        value = _status_from_changes(changes)
        if value:
            return value

    for key in _STATUS_FALLBACK_KEYS:
        value = _extract_string(event, (key,))
        if value:
            return value

    return None


def _status_from_changes(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key, nested_value in value.items():
            if _normalize_field_name(key) in _STATUS_FIELD_NAMES:
                status = _status_value_from_change(nested_value)
                if status:
                    return status

        field_name = _first_string(value, ("field", "fieldName", "field_name", "name", "key"))
        if field_name and _normalize_field_name(field_name) in _STATUS_FIELD_NAMES:
            status = _status_value_from_change(value)
            if status:
                return status

        for nested_value in value.values():
            status = _status_from_changes(nested_value)
            if status:
                return status

    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        for item in value:
            status = _status_from_changes(item)
            if status:
                return status

    return None


def _status_value_from_change(value: Any) -> str | None:
    if isinstance(value, str):
        return value

    if isinstance(value, Mapping):
        for key in (
            "newValue",
            "new_value",
            "to",
            "after",
            "value",
            "name",
            "status",
            "state",
            "workflowState",
            "workflow_state",
        ):
            status = _string_or_named_value(value.get(key))
            if status:
                return status

    return _string_or_named_value(value)


def _extract_string(event: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    candidates = tuple(_candidate_maps(event))
    for key in keys:
        for candidate in candidates:
            value = _first_string(candidate, (key,))
            if value:
                return value

    return None


def _first_string(mapping: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for key in keys:
        if key in mapping:
            value = _string_or_named_value(mapping[key])
            if value:
                return value
    return None


def _string_or_named_value(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "label", "displayName"):
            nested = _string_or_named_value(value.get(key))
            if nested:
                return nested

    return None


def _candidate_maps(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for key in ("triggerContext", "data", "issue"):
            nested = value.get(key)
            if isinstance(nested, Mapping):
                yield from _candidate_maps(nested)


def _values_for_keys(value: Any, keys: set[str]) -> Iterable[Any]:
    if isinstance(value, Mapping):
        for key, nested_value in value.items():
            if key in keys:
                yield nested_value
            yield from _values_for_keys(nested_value, keys)
    elif isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        for item in value:
            yield from _values_for_keys(item, keys)


def _already_prefixed(title: str) -> bool:
    return title.lstrip().casefold().startswith(PREFIX.casefold())


def _normalize_words(value: Any) -> str:
    if value is None:
        return ""

    text = str(value).strip()
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().casefold()


def _normalize_field_name(value: Any) -> str:
    return _normalize_words(value).replace(" ", "")


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    print(json.dumps(action, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
