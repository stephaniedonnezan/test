"""Build Linear issue-title updates for research status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELDS = {"status", "state", "workflow state", "workflowstate"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to research."""

    if not isinstance(event, Mapping):
        return None

    context = _mapping_value(event, "triggerContext")
    data = _mapping_value(event, "data")
    issue = _mapping_value(event, "issue") or _mapping_value(data, "issue")

    trigger_sources = _compact_mappings(context, event, data)
    if not _is_status_change_event(trigger_sources, event):
        return None

    status = _new_status(trigger_sources + _compact_mappings(issue), event)
    if _normalize(status) != TARGET_STATUS:
        return None

    issue_sources = _compact_mappings(context, issue, data, event)
    issue_id = _first_text(issue_sources, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_text(issue_sources, ("title", "issueTitle", "name"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if title.casefold().startswith(PREFIX.casefold()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _is_status_change_event(sources: list[Mapping[str, Any]], event: Mapping[str, Any]) -> bool:
    trigger_values = [
        value
        for source in sources
        for key in ("trigger", "webhookType", "action", "type", "eventType")
        if (value := _text_value(source.get(key)))
    ]
    normalized_values = {_normalize(value) for value in trigger_values}

    if any("status" in value and "changed" in value for value in normalized_values):
        return True
    if any("state" in value and "changed" in value for value in normalized_values):
        return True

    if normalized_values.intersection({"update", "updated", "issue updated", "updated issue"}):
        return _changed_fields_include_status(event)

    return False


def _changed_fields_include_status(event: Mapping[str, Any]) -> bool:
    for source in _all_mappings(event):
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            if _fields_include_status(source.get(key)):
                return True
        changes = source.get("changes")
        if isinstance(changes, Mapping):
            if any(_normalize(key) in _STATUS_FIELDS for key in changes):
                return True
        elif _fields_include_status(changes):
            return True
    return False


def _fields_include_status(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize(value) in _STATUS_FIELDS
    if isinstance(value, Mapping):
        field = _text_value(value.get("field") or value.get("name"))
        return bool(field and _normalize(field) in _STATUS_FIELDS)
    if isinstance(value, Iterable):
        return any(_fields_include_status(item) for item in value)
    return False


def _new_status(sources: list[Mapping[str, Any]], event: Mapping[str, Any]) -> str | None:
    for key in ("newStatus", "new_status", "toStatus", "to_status"):
        if status := _first_text(sources, (key,)):
            return status

    if status := _status_from_changes(event):
        return status

    for key in ("status", "state", "workflowState", "workflow_state"):
        if status := _first_text(sources, (key,)):
            return status

    return None


def _status_from_changes(event: Mapping[str, Any]) -> str | None:
    for source in _all_mappings(event):
        changes = source.get("changes")
        if not isinstance(changes, Mapping):
            continue
        for key, change in changes.items():
            if _normalize(key) not in _STATUS_FIELDS:
                continue
            if isinstance(change, Mapping):
                for value_key in ("to", "new", "newValue", "after"):
                    if status := _text_value(change.get(value_key)):
                        return status
            if status := _text_value(change):
                return status
    return None


def _all_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if not isinstance(value, Mapping):
        return
    yield value
    for nested_key in ("triggerContext", "data", "issue"):
        nested = value.get(nested_key)
        if isinstance(nested, Mapping):
            yield from _all_mappings(nested)


def _compact_mappings(*values: Any) -> list[Mapping[str, Any]]:
    return [value for value in values if isinstance(value, Mapping)]


def _mapping_value(source: Any, key: str) -> Mapping[str, Any] | None:
    if isinstance(source, Mapping) and isinstance(source.get(key), Mapping):
        return source[key]
    return None


def _first_text(sources: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for source in sources:
        for key in keys:
            if value := _text_value(source.get(key)):
                return value
    return None


def _text_value(value: Any) -> str | None:
    if isinstance(value, str):
        text = value.strip()
        return text or None
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            if text := _text_value(value.get(key)):
                return text
    return None


def _normalize(value: str | None) -> str | None:
    if value is None:
        return None
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value.strip())
    text = re.sub(r"[_\-\s]+", " ", text)
    return text.casefold()


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
