"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_DIRECT_STATUS_CHANGE_EVENTS = {
    "status changed",
    "status change",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
}
_GENERIC_UPDATE_EVENTS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}
_STATUS_FIELD_NAMES = {"status", "state", "workflowstate"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear issue-title update action for To Research status changes.

    The returned object is intentionally side-effect free so the caller can
    decide how to apply the update to Linear.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    if _normalize_text(_extract_status(event)) != TARGET_STATUS:
        return None

    issue_id = _extract_issue_id(event)
    title = _extract_title(event)
    if issue_id is None or title is None:
        return None

    if title.casefold().startswith(PREFIX.casefold()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def handle_issue_status_changed(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Compatibility wrapper for automation entrypoints."""

    return build_issue_title_update(event)


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    event_names = {
        _normalize_text(value)
        for mapping in _walk_mappings(event)
        for key in ("trigger", "webhookType", "action", "type")
        if (value := mapping.get(key)) is not None
    }

    if event_names & _DIRECT_STATUS_CHANGE_EVENTS:
        return True

    return bool(event_names & _GENERIC_UPDATE_EVENTS) and _has_updated_status_field(event)


def _has_updated_status_field(event: Mapping[str, Any]) -> bool:
    for mapping in _walk_mappings(event):
        updated_fields = mapping.get("updatedFields")
        if _contains_status_field(updated_fields):
            return True

        for changes_key in ("changes", "changed", "change"):
            changes = mapping.get(changes_key)
            if isinstance(changes, Mapping):
                if any(_is_status_field_name(key) for key in changes.keys()):
                    return True
                if _contains_status_field(changes.get("field")):
                    return True

    return False


def _contains_status_field(value: Any) -> bool:
    if value is None:
        return False

    if isinstance(value, str):
        return _is_status_field_name(value)

    if isinstance(value, Mapping):
        field = value.get("field") or value.get("name") or value.get("fieldName")
        if _contains_status_field(field):
            return True
        return any(_contains_status_field(item) for item in value.values())

    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        return any(_contains_status_field(item) for item in value)

    return False


def _is_status_field_name(value: Any) -> bool:
    normalized = re.sub(r"[^a-z0-9]", "", _normalize_text(value))
    return normalized in _STATUS_FIELD_NAMES


def _extract_status(event: Mapping[str, Any]) -> str | None:
    for value in _changed_status_values(event):
        status = _coerce_name(value)
        if status:
            return status

    explicit_keys = (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "newWorkflowState",
        "new_workflow_state",
        "statusName",
        "stateName",
        "workflowStateName",
    )
    for mapping in _walk_mappings(event):
        for key in explicit_keys:
            status = _coerce_name(mapping.get(key))
            if status:
                return status

    for mapping in _walk_mappings(event):
        for key in ("status", "state", "workflowState", "workflow_state"):
            status = _coerce_name(mapping.get(key))
            if status:
                return status

    return None


def _changed_status_values(event: Mapping[str, Any]) -> Iterable[Any]:
    for mapping in _walk_mappings(event):
        for changes_key in ("changes", "changed"):
            changes = mapping.get(changes_key)
            if not isinstance(changes, Mapping):
                continue

            for field_name, change in changes.items():
                if not _is_status_field_name(field_name):
                    continue

                if isinstance(change, Mapping):
                    for value_key in ("new", "to", "after", "current", "newValue", "toValue", "name"):
                        if value_key in change:
                            yield change[value_key]
                else:
                    yield change

        change = mapping.get("change")
        if isinstance(change, Mapping) and _contains_status_field(change.get("field")):
            for value_key in ("new", "to", "after", "current", "newValue", "toValue", "value"):
                if value_key in change:
                    yield change[value_key]


def _extract_issue_id(event: Mapping[str, Any]) -> str | None:
    for key_group in (
        ("issueId", "issue_id", "identifier", "key"),
        ("id",),
    ):
        for mapping in _walk_mappings(event):
            for key in key_group:
                value = _coerce_string(mapping.get(key))
                if value:
                    return value

    return None


def _extract_title(event: Mapping[str, Any]) -> str | None:
    for mapping in _walk_mappings(event):
        title = _coerce_string(mapping.get("title"))
        if title:
            return title

    return None


def _walk_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if not isinstance(value, Mapping):
        return

    yield value

    for nested_key in ("triggerContext", "context", "payload", "data", "issue"):
        nested = value.get(nested_key)
        if isinstance(nested, Mapping):
            yield from _walk_mappings(nested)


def _coerce_name(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            text = _coerce_name(value.get(key))
            if text:
                return text
        return None

    return _coerce_string(value)


def _coerce_string(value: Any) -> str | None:
    if value is None or isinstance(value, bool):
        return None

    text = str(value).strip()
    return text or None


def _normalize_text(value: Any) -> str:
    text = _coerce_string(value)
    if text is None:
        return ""

    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[_-]+", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().casefold()


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        json.dump(update, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
