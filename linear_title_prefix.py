"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"

_STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflowstatus"}
_NEW_STATUS_FIELD_NAMES = {
    "newstatus",
    "newstate",
    "newworkflowstate",
    "newworkflowstatus",
}
_TRIGGER_FIELD_NAMES = {"trigger", "action", "type", "webhooktype", "eventtype"}
_STATUS_CHANGE_TRIGGERS = {
    "status changed",
    "status change",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
    "workflow status changed",
    "workflow status change",
}
_GENERIC_UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear issue title update action when an issue moves to research."""
    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    new_status = _extract_new_status(event)
    if _normalize_status(new_status) != TARGET_STATUS:
        return None

    issue_id = _clean_text(_first_text(event, ("issueId", "issue_id", "identifier", "key", "id")))
    title = _clean_text(_first_text(event, ("title", "name")))
    if not issue_id or not title or _has_research_prefix(title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    trigger_values = {
        normalized
        for value in _values_for_normalized_keys(event, _TRIGGER_FIELD_NAMES)
        if (normalized := _normalize_label(_text_or_name(value)))
    }

    if trigger_values & _STATUS_CHANGE_TRIGGERS:
        return True

    if trigger_values & _GENERIC_UPDATE_TRIGGERS:
        return _updated_fields_include_status(event) or _changes_include_status(event)

    # Cursor automation payloads can include the changed status without an
    # explicit trigger field; accept them only when status-change hints exist.
    return _updated_fields_include_status(event) or _changes_include_status(event)


def _extract_new_status(event: Mapping[str, Any]) -> str | None:
    for value in _values_for_normalized_keys(event, _NEW_STATUS_FIELD_NAMES):
        text = _text_or_name(value)
        if text:
            return text

    for change in _iter_change_mappings(event):
        key = _normalize_key(_text_or_name(change.get("field") or change.get("name") or change.get("key")))
        if key in _STATUS_FIELD_NAMES:
            for candidate_key in ("newValue", "new_value", "to", "after", "value"):
                text = _text_or_name(change.get(candidate_key))
                if text:
                    return text

    for value in _values_for_normalized_keys(event, _STATUS_FIELD_NAMES):
        text = _text_or_name(value)
        if text:
            return text

    return None


def _first_text(event: Mapping[str, Any], keys: Sequence[str]) -> str | None:
    for key in keys:
        for value in _values_for_normalized_keys(event, {_normalize_key(key)}):
            text = _text_or_name(value)
            if text:
                return text
    return None


def _values_for_normalized_keys(value: Any, normalized_keys: set[str]) -> list[Any]:
    values: list[Any] = []

    def visit(current: Any) -> None:
        if isinstance(current, Mapping):
            for key, item in current.items():
                if _normalize_key(str(key)) in normalized_keys:
                    values.append(item)
                visit(item)
        elif _is_sequence(current):
            for item in current:
                visit(item)

    visit(value)
    return values


def _updated_fields_include_status(event: Mapping[str, Any]) -> bool:
    for value in _values_for_normalized_keys(event, {"updatedfields", "changedfields"}):
        for field in _flatten_field_names(value):
            if _normalize_key(field) in _STATUS_FIELD_NAMES:
                return True
    return False


def _changes_include_status(event: Mapping[str, Any]) -> bool:
    for change in _iter_change_mappings(event):
        field = change.get("field") or change.get("name") or change.get("key")
        if _normalize_key(_text_or_name(field)) in _STATUS_FIELD_NAMES:
            return True
    return False


def _iter_change_mappings(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    changes: list[Mapping[str, Any]] = []
    for value in _values_for_normalized_keys(event, {"changes", "changed"}):
        if isinstance(value, Mapping):
            for key, item in value.items():
                if _normalize_key(str(key)) in _STATUS_FIELD_NAMES:
                    if isinstance(item, Mapping):
                        changes.append({"field": key, **item})
                    else:
                        changes.append({"field": key, "value": item})
                elif isinstance(item, Mapping):
                    changes.append(item)
        elif _is_sequence(value):
            changes.extend(item for item in value if isinstance(item, Mapping))
    return changes


def _flatten_field_names(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, Mapping):
        return [str(key) for key in value.keys()]
    if _is_sequence(value):
        fields: list[str] = []
        for item in value:
            if isinstance(item, Mapping):
                fields.extend(str(key) for key in item.keys())
                name = item.get("field") or item.get("name") or item.get("key")
                if name:
                    fields.append(str(name))
            else:
                fields.append(str(item))
        return fields
    return []


def _text_or_name(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        for key in ("name", "title", "label", "value"):
            text = _text_or_name(value.get(key))
            if text:
                return text
    return None


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _has_research_prefix(title: str) -> bool:
    return title.strip().lower().startswith(TITLE_PREFIX.lower())


def _normalize_status(value: str | None) -> str | None:
    normalized = _normalize_label(value)
    return normalized if normalized else None


def _normalize_label(value: str | None) -> str:
    if not value:
        return ""
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return re.sub(r"[^a-z0-9]+", " ", spaced.lower()).strip()


def _normalize_key(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _is_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))


def main() -> int:
    """Read a JSON event from stdin and print the requested title update."""
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    update = build_issue_title_update(event)
    print(json.dumps(update, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
