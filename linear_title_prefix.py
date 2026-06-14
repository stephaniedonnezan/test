"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"

_DIRECT_STATUS_CHANGE_EVENTS = {
    "status changed",
    "status change",
    "status updated",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow status changed",
}
_GENERIC_UPDATE_EVENTS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}
_STATUS_FIELD_KEYS = {
    "status",
    "state",
    "workflowstate",
    "workflowstatus",
}


def build_issue_title_update(event: Any) -> dict[str, str] | None:
    """Return an issue-title update action when a Linear issue enters research."""

    if not isinstance(event, Mapping):
        return None

    mappings = list(_walk_mappings(event))
    if not _is_status_change_event(mappings):
        return None

    new_status = _find_new_status(mappings)
    if _normalize_text(new_status) != RESEARCH_STATUS:
        return None

    issue_id = _find_first_string(mappings, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _find_first_string(mappings, ("title",))
    if not issue_id or not title:
        return None

    title = title.strip()
    if not title or _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _walk_mappings(value: Any, *, max_depth: int = 6) -> Iterable[Mapping[str, Any]]:
    if max_depth < 0 or not isinstance(value, Mapping):
        return

    yield value
    for nested in value.values():
        if isinstance(nested, Mapping):
            yield from _walk_mappings(nested, max_depth=max_depth - 1)
        elif isinstance(nested, list):
            for item in nested:
                if isinstance(item, Mapping):
                    yield from _walk_mappings(item, max_depth=max_depth - 1)


def _is_status_change_event(mappings: list[Mapping[str, Any]]) -> bool:
    event_names = {
        _normalize_text(mapping[key])
        for mapping in mappings
        for key in ("trigger", "webhookType", "action", "type")
        if key in mapping
    }

    if event_names & _DIRECT_STATUS_CHANGE_EVENTS:
        return True

    return bool(event_names & _GENERIC_UPDATE_EVENTS) and _updated_fields_include_status(mappings)


def _updated_fields_include_status(mappings: list[Mapping[str, Any]]) -> bool:
    for mapping in mappings:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            fields = mapping.get(key)
            if isinstance(fields, Mapping):
                names = fields.keys()
            elif isinstance(fields, list | tuple | set):
                names = fields
            else:
                continue

            if any(_is_status_field_name(field) for field in names):
                return True

        for key in ("changes", "changed", "previousValues", "previous_values"):
            changes = mapping.get(key)
            if isinstance(changes, Mapping) and any(_is_status_field_name(field) for field in changes):
                return True

    return False


def _find_new_status(mappings: list[Mapping[str, Any]]) -> str | None:
    direct_status_keys = (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "newWorkflowState",
        "new_workflow_state",
        "toStatus",
        "to_status",
        "statusName",
        "status_name",
        "stateName",
        "state_name",
        "workflowStateName",
        "workflow_state_name",
    )
    status_keys = ("status", "state", "workflowState", "workflow_state")

    value = _find_first_status_string(mappings, direct_status_keys)
    if value:
        return value

    value = _find_status_from_changes(mappings)
    if value:
        return value

    return _find_first_status_string(mappings, status_keys)


def _find_status_from_changes(mappings: list[Mapping[str, Any]]) -> str | None:
    for mapping in mappings:
        for key in ("changes", "changed"):
            changes = mapping.get(key)
            if not isinstance(changes, Mapping):
                continue

            for field, change in changes.items():
                if not _is_status_field_name(field):
                    continue

                status = _string_from_value(change, ("new", "to", "after", "name", "value"))
                if status:
                    return status

    return None


def _find_first_status_string(mappings: list[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for key in keys:
        for mapping in mappings:
            if key not in mapping:
                continue

            value = _string_from_value(mapping[key], ("name", "new", "to", "after", "value"))
            if value:
                return value

    return None


def _find_first_string(mappings: list[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for key in keys:
        for mapping in mappings:
            value = mapping.get(key)
            if isinstance(value, str) and value.strip():
                return value

    return None


def _string_from_value(value: Any, nested_keys: Iterable[str]) -> str | None:
    if isinstance(value, str) and value.strip():
        return value

    if isinstance(value, Mapping):
        for key in nested_keys:
            nested = value.get(key)
            if isinstance(nested, str) and nested.strip():
                return nested

    return None


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(TITLE_PREFIX.casefold())


def _is_status_field_name(value: Any) -> bool:
    return _normalize_field_name(value) in _STATUS_FIELD_KEYS


def _normalize_field_name(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", _normalize_text(value))


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""

    text = str(value).strip()
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().casefold()


def main() -> int:
    event = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(event), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
