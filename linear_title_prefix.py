"""Build Linear issue title updates for Cursor research automation."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"

_STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow_state"}
_EXPLICIT_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "toStatus",
    "to_status",
    "newState",
    "new_state",
    "newWorkflowState",
    "new_workflow_state",
    "statusName",
    "status_name",
    "stateName",
    "state_name",
    "workflowStateName",
    "workflow_state_name",
)
_ISSUE_ID_KEYS = ("issueId", "issue_id", "id", "identifier", "key")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to To Research."""
    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    new_status = _extract_new_status(event)
    if _normalize_status(new_status) != TARGET_STATUS:
        return None

    title = _extract_issue_title(event)
    issue_id = _extract_issue_id(event)
    if not title or not issue_id:
        return None

    clean_title = title.strip()
    if _has_research_prefix(clean_title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {clean_title}",
    }


def handle_issue_status_changed(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Compatibility alias for JavaScript-style automation entrypoints."""
    return build_issue_title_update(event)


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    trigger_values = list(_iter_trigger_values(event))
    if any(_is_direct_status_change(value) for value in trigger_values):
        return True

    if any(_is_generic_update(value) for value in trigger_values):
        return _has_status_field_change(event)

    # Some webhook wrappers omit the generic update marker but still include
    # changed status fields. Treat those as status-change events.
    return _has_status_field_change(event)


def _iter_trigger_values(value: Any) -> Iterable[Any]:
    if isinstance(value, Mapping):
        for key, nested_value in value.items():
            normalized_key = _normalize_key(key)
            if normalized_key in {
                "trigger",
                "action",
                "type",
                "event",
                "eventtype",
                "event_type",
                "webhooktype",
                "webhook_type",
            }:
                yield nested_value
            yield from _iter_trigger_values(nested_value)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_trigger_values(item)


def _is_direct_status_change(value: Any) -> bool:
    normalized = _normalize_status(value)
    return normalized in {
        "status changed",
        "status change",
        "state changed",
        "state change",
        "workflow state changed",
        "workflow state change",
        "issue status changed",
        "issue status change",
    }


def _is_generic_update(value: Any) -> bool:
    normalized = _normalize_status(value)
    return normalized in {"update", "updated", "issue update", "issue updated"}


def _has_status_field_change(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, nested_value in value.items():
            normalized_key = _normalize_key(key)
            if normalized_key in {"updatedfields", "changedfields"}:
                if _fields_include_status(nested_value):
                    return True
            if normalized_key in {"changes", "updatedfrom", "updated_from"}:
                if _changes_include_status(nested_value):
                    return True
            if _has_status_field_change(nested_value):
                return True
    elif isinstance(value, list):
        return any(_has_status_field_change(item) for item in value)
    return False


def _fields_include_status(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_key(value) in _STATUS_FIELD_NAMES
    if isinstance(value, Mapping):
        return any(
            _normalize_key(key) in _STATUS_FIELD_NAMES or _fields_include_status(nested)
            for key, nested in value.items()
        )
    if isinstance(value, Iterable):
        return any(_fields_include_status(item) for item in value)
    return False


def _changes_include_status(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(
            _normalize_key(key) in _STATUS_FIELD_NAMES or _changes_include_status(nested)
            for key, nested in value.items()
        )
    if isinstance(value, list):
        return any(_changes_include_status(item) for item in value)
    return False


def _extract_new_status(event: Mapping[str, Any]) -> str | None:
    for context in _iter_contexts(event):
        for key in _EXPLICIT_STATUS_KEYS:
            status = _coerce_name(context.get(key))
            if status:
                return status

    changed_status = _extract_status_from_changes(event)
    if changed_status:
        return changed_status

    for context in _iter_contexts(event):
        for key in ("status", "state", "workflowState", "workflow_state"):
            status = _coerce_name(context.get(key))
            if status:
                return status

    return None


def _extract_status_from_changes(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key, nested_value in value.items():
            normalized_key = _normalize_key(key)
            if normalized_key in {"updatedfrom", "updated_from"}:
                continue
            if normalized_key in _STATUS_FIELD_NAMES:
                status = _extract_new_value(nested_value)
                if status:
                    return status
            if normalized_key == "changes":
                status = _extract_new_value(nested_value)
                if status:
                    return status
            status = _extract_status_from_changes(nested_value)
            if status:
                return status
    elif isinstance(value, list):
        for item in value:
            status = _extract_status_from_changes(item)
            if status:
                return status
    return None


def _extract_new_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("newValue", "new_value", "new", "to", "after", "name"):
            status = _coerce_name(value.get(key))
            if status:
                return status
        for nested in value.values():
            status = _extract_new_value(nested)
            if status:
                return status
    else:
        return _coerce_name(value)
    return None


def _extract_issue_title(event: Mapping[str, Any]) -> str | None:
    for context in _iter_contexts(event):
        title = _coerce_string(context.get("title"))
        if title:
            return title
    return None


def _extract_issue_id(event: Mapping[str, Any]) -> str | None:
    for context in _iter_contexts(event):
        for key in _ISSUE_ID_KEYS:
            issue_id = _coerce_string(context.get(key))
            if issue_id:
                return issue_id
    return None


def _iter_contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    seen: set[int] = set()
    for value in (
        event.get("triggerContext"),
        event.get("trigger_context"),
        event,
        event.get("issue"),
        event.get("data"),
    ):
        yield from _walk_mappings(value, seen)


def _walk_mappings(value: Any, seen: set[int]) -> Iterable[Mapping[str, Any]]:
    if not isinstance(value, Mapping):
        return

    object_id = id(value)
    if object_id in seen:
        return
    seen.add(object_id)

    yield value
    for nested_value in value.values():
        if isinstance(nested_value, Mapping):
            yield from _walk_mappings(nested_value, seen)
        elif isinstance(nested_value, list):
            for item in nested_value:
                yield from _walk_mappings(item, seen)


def _coerce_name(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            result = _coerce_string(value.get(key))
            if result:
                return result
        return None
    return _coerce_string(value)


def _coerce_string(value: Any) -> str | None:
    if isinstance(value, str):
        trimmed = value.strip()
        return trimmed or None
    return None


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def _normalize_status(value: Any) -> str:
    text = _coerce_name(value)
    if not text:
        return ""

    separated = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    separated = re.sub(r"[_-]+", " ", separated)
    separated = re.sub(r"[^A-Za-z0-9]+", " ", separated)
    return re.sub(r"\s+", " ", separated).strip().lower()


def _normalize_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9_]+", "", str(value).strip().lower())


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    print(json.dumps(update, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
