"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow state"}
_NEW_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "newWorkflowState",
    "new_workflow_state",
)
_DIRECT_STATUS_KEYS = ("status", "state", "workflowState", "workflow_state")
_TRIGGER_KEYS = ("trigger", "webhookType", "webhook_type", "action", "type")
_UPDATE_EVENTS = {"update", "updated", "issue updated", "updated issue"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue-title update action when an issue enters To Research.

    The Cursor automation payload is flat under ``triggerContext`` while Linear
    webhooks can contain the issue under ``data.issue``. This function accepts
    both shapes and returns a small action object for the caller to apply.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    status = _find_new_status(event)
    if _normalize_text(status) != TARGET_STATUS:
        return None

    issue_id = _find_first_text(event, ("issueId", "issue_id", "id", "identifier", "key"))
    title = _find_first_text(event, ("title",))
    if issue_id is None or title is None:
        return None

    title = title.strip()
    if not title or _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    trigger_values = [
        _normalize_text(value)
        for mapping in _walk_mappings(event)
        for key, value in mapping.items()
        if key in _TRIGGER_KEYS
    ]

    if any("status changed" in value or value == "status change" for value in trigger_values):
        return True

    return any(value in _UPDATE_EVENTS for value in trigger_values) and _status_field_changed(event)


def _status_field_changed(event: Mapping[str, Any]) -> bool:
    for mapping in _walk_mappings(event):
        for key in ("updatedFields", "updated_fields"):
            fields = mapping.get(key)
            if _contains_status_field(fields):
                return True

        changes = mapping.get("changes")
        if isinstance(changes, Mapping) and any(_is_status_field(key) for key in changes):
            return True

    return False


def _find_new_status(event: Mapping[str, Any]) -> str | None:
    for mapping in _walk_mappings(event):
        for key in _NEW_STATUS_KEYS:
            if key in mapping:
                status = _extract_name(mapping[key])
                if status:
                    return status

    for mapping in _walk_mappings(event):
        changes = mapping.get("changes")
        if not isinstance(changes, Mapping):
            continue

        for key, value in changes.items():
            if not _is_status_field(key):
                continue

            status = _extract_changed_to_value(value)
            if status:
                return status

    for mapping in _walk_mappings(event):
        for key in _DIRECT_STATUS_KEYS:
            if key in mapping:
                status = _extract_name(mapping[key])
                if status:
                    return status

    return None


def _extract_changed_to_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("to", "after", "new", "newValue", "new_value", "name"):
            if key in value:
                status = _extract_name(value[key])
                if status:
                    return status

    return _extract_name(value)


def _extract_name(value: Any) -> str | None:
    if isinstance(value, str):
        return value

    if isinstance(value, Mapping):
        for key in ("name", "title", "label", "status", "state", "workflowState"):
            if key in value:
                nested = _extract_name(value[key])
                if nested:
                    return nested

    return None


def _find_first_text(event: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    key_set = set(keys)
    for mapping in _walk_mappings(event):
        for key in keys:
            if key in mapping and key in key_set and isinstance(mapping[key], str) and mapping[key].strip():
                return mapping[key]

    return None


def _contains_status_field(fields: Any) -> bool:
    if isinstance(fields, str):
        return _is_status_field(fields)

    if isinstance(fields, Mapping):
        return any(_is_status_field(key) for key in fields)

    if isinstance(fields, Iterable):
        return any(isinstance(field, str) and _is_status_field(field) for field in fields)

    return False


def _is_status_field(value: Any) -> bool:
    return isinstance(value, str) and _normalize_text(value) in _STATUS_FIELD_NAMES


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def _walk_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for child in value.values():
            yield from _walk_mappings(child)
    elif isinstance(value, list | tuple):
        for child in value:
            yield from _walk_mappings(child)


def _normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    split_camel = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    normalized = re.sub(r"[^a-zA-Z0-9]+", " ", split_camel).strip().lower()
    return re.sub(r"\s+", " ", normalized)


def main() -> int:
    event = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(event), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
