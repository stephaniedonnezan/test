"""Build Linear issue-title update actions for research status changes.

The automation runner passes Linear webhook data in a few shapes.  This module
keeps the public behavior small: return an update action only when an issue is
moving into the "to research" status and its title does not already have the
Cursor research prefix.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow_state"}
_STATUS_EVENT_NAMES = {
    "statuschanged",
    "issuestatuschanged",
    "linearissuestatuschanged",
}
_ISSUE_UPDATE_EVENT_NAMES = {
    "update",
    "updated",
    "issueupdate",
    "issueupdated",
    "updatedissue",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action for a matching status-change event.

    The returned action is intentionally data-only so callers can decide how to
    execute it against Linear.
    """

    if not isinstance(event, Mapping):
        return None

    mappings = list(_iter_mappings(event))
    if not _is_status_change_event(mappings):
        return None

    new_status = _extract_new_status(mappings)
    if _normalize_words(new_status) != TARGET_STATUS:
        return None

    issue_id = _extract_issue_id(event)
    title = _extract_issue_title(event)
    if not issue_id or not title or _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _iter_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for nested_value in value.values():
            yield from _iter_mappings(nested_value)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_mappings(item)


def _is_status_change_event(mappings: list[Mapping[str, Any]]) -> bool:
    for mapping in mappings:
        for key in ("trigger", "webhookType", "eventType", "action", "type"):
            event_name = _compact_words(mapping.get(key))
            if event_name in _STATUS_EVENT_NAMES:
                return True
            if event_name in _ISSUE_UPDATE_EVENT_NAMES and _updated_fields_include_status(mappings):
                return True
    return False


def _updated_fields_include_status(mappings: list[Mapping[str, Any]]) -> bool:
    for mapping in mappings:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            if _contains_status_field(mapping.get(key)):
                return True

        changes = mapping.get("changes")
        if isinstance(changes, Mapping):
            if any(_is_status_field_name(key) for key in changes):
                return True
        elif _contains_status_field(changes):
            return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field_name(value)
    if isinstance(value, Mapping):
        field_name = value.get("field") or value.get("name") or value.get("key")
        return _is_status_field_name(field_name) or any(
            _contains_status_field(nested_value) for nested_value in value.values()
        )
    if isinstance(value, list):
        return any(_contains_status_field(item) for item in value)
    return False


def _is_status_field_name(value: Any) -> bool:
    return _compact_words(value) in _STATUS_FIELD_NAMES


def _extract_new_status(mappings: list[Mapping[str, Any]]) -> str | None:
    for mapping in mappings:
        for key in (
            "newStatus",
            "new_status",
            "toStatus",
            "to_status",
            "newState",
            "new_state",
            "toState",
            "to_state",
            "newWorkflowState",
            "new_workflow_state",
            "statusName",
            "status_name",
        ):
            status = _status_text(mapping.get(key))
            if status:
                return status

    for mapping in mappings:
        for key in ("changes", "updatedFields", "updated_fields", "changedFields", "changed_fields"):
            status = _status_from_change_container(mapping.get(key))
            if status:
                return status

    for mapping in mappings:
        for key in ("status", "state", "workflowState", "workflow_state"):
            status = _status_text(mapping.get(key))
            if status:
                return status

    return None


def _status_from_change_container(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key, changed_value in value.items():
            if _is_status_field_name(key):
                status = _status_from_changed_value(changed_value)
                if status:
                    return status
        return None

    if isinstance(value, list):
        for item in value:
            if isinstance(item, Mapping):
                field_name = item.get("field") or item.get("name") or item.get("key")
                if _is_status_field_name(field_name):
                    status = _status_from_changed_value(item)
                    if status:
                        return status
        for item in value:
            status = _status_from_change_container(item)
            if status:
                return status

    return None


def _status_from_changed_value(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None

    if isinstance(value, Mapping):
        for key in (
            "to",
            "toName",
            "to_name",
            "newValue",
            "new_value",
            "new",
            "after",
            "name",
            "value",
        ):
            status = _status_text(value.get(key))
            if status:
                return status

    return _status_text(value)


def _status_text(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, Mapping):
        for key in ("name", "title", "label", "value"):
            status = _status_text(value.get(key))
            if status:
                return status
    return None


def _extract_issue_id(event: Mapping[str, Any]) -> str | None:
    return _extract_issue_value(event, ("issueId", "issue_id", "identifier", "key", "id"))


def _extract_issue_title(event: Mapping[str, Any]) -> str | None:
    return _extract_issue_value(event, ("title", "issueTitle", "issue_title"))


def _extract_issue_value(event: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for mapping in _issue_contexts(event):
        for key in keys:
            value = mapping.get(key)
            if isinstance(value, str):
                cleaned = value.strip()
                if cleaned:
                    return cleaned
    return None


def _issue_contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    for path in (
        ("automation_trigger_info", "triggerContext"),
        ("automationTriggerInfo", "triggerContext"),
        ("triggerContext",),
        ("data", "issue"),
        ("payload", "issue"),
        ("issue",),
        ("data",),
        ("payload",),
    ):
        mapping = _mapping_at_path(event, path)
        if mapping is not None:
            yield mapping

    yield event


def _mapping_at_path(mapping: Mapping[str, Any], path: tuple[str, ...]) -> Mapping[str, Any] | None:
    current: Any = mapping
    for key in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current if isinstance(current, Mapping) else None


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def _normalize_words(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return re.sub(r"[^a-z0-9]+", " ", spaced.lower()).strip()


def _compact_words(value: Any) -> str:
    return _normalize_words(value).replace(" ", "")


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON payload: {exc}", file=sys.stderr)
        return 1

    update = build_issue_title_update(event)
    print(json.dumps(update, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
