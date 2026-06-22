"""Build Linear issue title update actions for Cursor research automation.

The automation receives payloads from either Cursor's flattened
``triggerContext`` or Linear's nested webhook shape.  This module keeps the
decision pure and side-effect free: callers can apply the returned action with
their Linear client.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflowstate",
    "workflowstatus",
    "stateid",
    "statusid",
    "workflowstateid",
}
STATUS_VALUE_KEYS = (
    "newStatus",
    "new_status",
    "status",
    "state",
    "workflowState",
    "workflow_status",
    "workflowStatus",
)
TRIGGER_KEYS = ("trigger", "webhookType", "webhook_type", "action", "type")
STATUS_TRIGGER_VALUES = {
    "statuschanged",
    "statuschange",
    "statusupdated",
    "statechanged",
    "stateupdated",
    "workflowstatechanged",
    "workflowstateupdated",
}
GENERIC_UPDATE_VALUES = {
    "update",
    "updated",
    "issueupdated",
    "updatedissue",
    "issueupdate",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when an issue moves to "to research".

    The returned dictionary is intentionally simple JSON-serializable data:
    ``{"action": "update_issue_title", "issueId": "...", "title": "..."}``.
    """

    if not isinstance(event, Mapping):
        return None

    records = _records(event)
    if not _is_status_change(records):
        return None

    status = _first_text(_status_candidates(records))
    if _normalize_text(status) != _normalize_text(TARGET_STATUS):
        return None

    issue_id = _first_text(_value_candidates(records, ("issueId", "issue_id", "id", "identifier", "key")))
    title = _first_text(_value_candidates(records, ("title", "name")))
    if not issue_id or not title:
        return None

    if _has_prefix(title):
        updated_title = title
    else:
        updated_title = f"{PREFIX}: {title}"

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": updated_title,
    }


def _records(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return useful mapping records from outer metadata to nested issue data."""

    records: list[Mapping[str, Any]] = [event]
    for key in ("triggerContext", "data", "issue"):
        value = event.get(key)
        if isinstance(value, Mapping):
            records.extend(_records(value))

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            records.extend(_records(issue))

    # Preserve order while removing duplicate mapping objects.
    unique: list[Mapping[str, Any]] = []
    seen: set[int] = set()
    for record in records:
        marker = id(record)
        if marker not in seen:
            seen.add(marker)
            unique.append(record)
    return unique


def _is_status_change(records: Iterable[Mapping[str, Any]]) -> bool:
    records = list(records)
    trigger_values = [
        _normalize_text(value)
        for record in records
        for key in TRIGGER_KEYS
        for value in _iter_values(record.get(key))
    ]

    if any(value in STATUS_TRIGGER_VALUES for value in trigger_values):
        return True

    if any(value in GENERIC_UPDATE_VALUES for value in trigger_values):
        return any(_mentions_status_field(value) for record in records for value in _change_field_candidates(record))

    if trigger_values:
        return False

    # Cursor automations sometimes provide a status-focused payload without an
    # explicit trigger name. In that case, the new status field is sufficient.
    return any(_first_text(_status_candidates([record])) for record in records)


def _status_candidates(records: Iterable[Mapping[str, Any]]) -> Iterable[Any]:
    for record in records:
        for key in STATUS_VALUE_KEYS:
            if key in record:
                yield _status_value(record[key])
        for container_key in ("changes", "updatedFields"):
            yield from _status_from_change_container(record.get(container_key))


def _status_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        for key in ("name", "newValue", "to", "value", "displayName"):
            if key in value:
                return _status_value(value[key])
    return value


def _status_from_change_container(container: Any) -> Iterable[Any]:
    if isinstance(container, Mapping):
        for key, value in container.items():
            if _mentions_status_field(key):
                yield _status_value(value)
            elif isinstance(value, Mapping) and _mentions_status_field(value.get("field") or value.get("name")):
                yield _status_value(value)
    elif isinstance(container, list):
        for item in container:
            if isinstance(item, Mapping):
                field_name = item.get("field") or item.get("name") or item.get("fieldName")
                if _mentions_status_field(field_name):
                    yield _status_value(item)


def _change_field_candidates(record: Mapping[str, Any]) -> Iterable[Any]:
    for key in ("updatedFields", "changedFields", "changes"):
        value = record.get(key)
        if isinstance(value, Mapping):
            yield from value.keys()
            for item in value.values():
                if isinstance(item, Mapping):
                    yield item.get("field")
                    yield item.get("name")
                    yield item.get("fieldName")
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, Mapping):
                    yield item.get("field")
                    yield item.get("name")
                    yield item.get("fieldName")
                else:
                    yield item


def _value_candidates(records: Iterable[Mapping[str, Any]], keys: tuple[str, ...]) -> Iterable[Any]:
    for record in records:
        for key in keys:
            if key in record:
                yield record[key]


def _iter_values(value: Any) -> Iterable[Any]:
    if isinstance(value, list):
        yield from value
    else:
        yield value


def _first_text(values: Iterable[Any]) -> str | None:
    for value in values:
        if isinstance(value, Mapping):
            value = _status_value(value)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _mentions_status_field(value: Any) -> bool:
    if value is None:
        return False
    normalized = _normalize_text(str(value))
    return normalized in STATUS_FIELD_NAMES


def _normalize_text(value: str | None) -> str:
    if value is None:
        return ""
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", str(value))
    return re.sub(r"[^a-z0-9]+", "", spaced.casefold())


def _has_prefix(title: str) -> bool:
    normalized_title = _normalize_text(title)
    normalized_prefix = _normalize_text(PREFIX)
    return normalized_title.startswith(normalized_prefix)


def main() -> int:
    """Read a JSON event from stdin and print the computed action, if any."""

    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
