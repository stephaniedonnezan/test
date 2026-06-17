"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {
    "status",
    "status id",
    "state",
    "state id",
    "workflow state",
    "workflow state id",
    "workflowstate",
    "workflowstate id",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue enters "to research"."""
    if not isinstance(event, Mapping):
        return None

    mappings = list(_iter_mappings(event))
    if not _is_status_change_event(mappings):
        return None

    new_status = _extract_status(mappings)
    if _normalize_text(new_status) != TARGET_STATUS:
        return None

    issue_id = _extract_issue_id(mappings)
    title = _extract_title(mappings)
    if not issue_id or not title:
        return None

    if title.casefold().startswith(TITLE_PREFIX.casefold()):
        prefixed_title = title
    else:
        prefixed_title = f"{TITLE_PREFIX}: {title}"

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": prefixed_title,
    }


def _iter_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for nested in value.values():
            yield from _iter_mappings(nested)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_mappings(item)


def _is_status_change_event(mappings: list[Mapping[str, Any]]) -> bool:
    metadata = []
    for mapping in mappings:
        for key in ("trigger", "eventType", "action", "type"):
            value = _string_value(mapping.get(key))
            if value:
                metadata.append(_normalize_text(value))

    if any(_is_direct_status_change(value) for value in metadata):
        return True

    return any(_is_issue_update(value) for value in metadata) and _has_status_update_marker(
        mappings
    )


def _is_direct_status_change(value: str) -> bool:
    return (
        value in {"status changed", "status change", "state changed", "state change"}
        or ("status" in value and "changed" in value)
        or ("state" in value and "changed" in value)
    )


def _is_issue_update(value: str) -> bool:
    return value in {"update", "updated", "issue update", "issue updated", "updated issue"}


def _has_status_update_marker(mappings: list[Mapping[str, Any]]) -> bool:
    for mapping in mappings:
        for key in ("updatedFields", "changedFields", "changes", "updatedFrom"):
            if key in mapping and _contains_status_field(mapping[key]):
                return True
    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field_name(value)
    if isinstance(value, Mapping):
        return any(_is_status_field_name(key) for key in value.keys())
    if isinstance(value, list):
        return any(_contains_status_field(item) for item in value)
    return False


def _is_status_field_name(value: Any) -> bool:
    normalized = _normalize_text(_string_value(value))
    return normalized in _STATUS_FIELD_NAMES


def _extract_status(mappings: list[Mapping[str, Any]]) -> str | None:
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
    for mapping in mappings:
        for key in explicit_keys:
            value = _string_or_name(mapping.get(key))
            if value:
                return value

    for mapping in mappings:
        for key in ("status", "state", "workflowState", "workflow_state"):
            value = _string_or_name(mapping.get(key))
            if value:
                return value

    return None


def _extract_issue_id(mappings: list[Mapping[str, Any]]) -> str | None:
    for keys in (
        ("identifier", "key", "issueId", "issue_id"),
        ("id",),
    ):
        for mapping in mappings:
            for key in keys:
                value = _string_value(mapping.get(key))
                if value:
                    return value.strip()
    return None


def _extract_title(mappings: list[Mapping[str, Any]]) -> str | None:
    for mapping in mappings:
        value = _string_value(mapping.get("title"))
        if value and value.strip():
            return value.strip()
    return None


def _string_or_name(value: Any) -> str | None:
    direct = _string_value(value)
    if direct:
        return direct.strip()
    if isinstance(value, Mapping):
        named = _string_value(value.get("name"))
        if named:
            return named.strip()
    return None


def _string_value(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    return None


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return re.sub(r"[^a-z0-9]+", " ", spaced.casefold()).strip()


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    print(json.dumps(action, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
