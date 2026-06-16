"""Build Linear issue-title updates for issues entering research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow state"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue-title update action when a Linear issue enters research."""
    if not isinstance(event, Mapping):
        return None

    records = _flatten_mappings(event)
    if not _is_status_change_event(records):
        return None

    new_status = _extract_new_status(records)
    if _normalize_text(new_status) != TARGET_STATUS:
        return None

    issue_id = _extract_issue_id(records)
    title = _extract_title(records)
    if not issue_id or not title:
        return None

    if title.lower().startswith(TITLE_PREFIX.lower()):
        updated_title = title
    else:
        updated_title = f"{TITLE_PREFIX}: {title}"

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": updated_title,
    }


def _flatten_mappings(value: Any) -> list[Mapping[str, Any]]:
    records: list[Mapping[str, Any]] = []

    def visit(node: Any) -> None:
        if isinstance(node, Mapping):
            records.append(node)
            for child in node.values():
                visit(child)
        elif isinstance(node, list):
            for child in node:
                visit(child)

    visit(value)
    return records


def _is_status_change_event(records: list[Mapping[str, Any]]) -> bool:
    event_names = []
    for record in records:
        for key in ("trigger", "webhookType", "webhook_type", "action", "type", "eventType"):
            value = record.get(key)
            if isinstance(value, str):
                event_names.append(_normalize_text(value))

    if any(name in {"status changed", "statuschanged"} for name in event_names):
        return True

    if any(name in {"issue updated", "updated issue", "update"} for name in event_names):
        return _updated_fields_include_status(records) or _changes_include_status(records)

    return _updated_fields_include_status(records) or _changes_include_status(records)


def _updated_fields_include_status(records: list[Mapping[str, Any]]) -> bool:
    for record in records:
        updated_fields = record.get("updatedFields") or record.get("updated_fields")
        if isinstance(updated_fields, str):
            fields = [updated_fields]
        elif isinstance(updated_fields, list):
            fields = updated_fields
        else:
            continue

        for field in fields:
            if _is_status_field(field):
                return True
    return False


def _changes_include_status(records: list[Mapping[str, Any]]) -> bool:
    for record in records:
        changes = record.get("changes") or record.get("changed")
        if not isinstance(changes, Mapping):
            continue

        for field in changes:
            if _is_status_field(field):
                return True
    return False


def _extract_new_status(records: list[Mapping[str, Any]]) -> str | None:
    explicit_status_keys = (
        "newStatus",
        "new_status",
        "newStatusName",
        "new_status_name",
        "toStatus",
        "to_status",
        "targetStatus",
        "target_status",
    )
    for record in records:
        value = _first_string(record, explicit_status_keys)
        if value:
            return value

    for record in records:
        value = _new_value_from_changes(record.get("changes") or record.get("changed"))
        if value:
            return value

    for record in records:
        value = _status_name_from_record(record)
        if value:
            return value

    return None


def _new_value_from_changes(changes: Any) -> str | None:
    if not isinstance(changes, Mapping):
        return None

    for field, change in changes.items():
        if not _is_status_field(field):
            continue

        if isinstance(change, str):
            return change.strip() or None
        if not isinstance(change, Mapping):
            continue

        value = _first_string(
            change,
            (
                "newValue",
                "new_value",
                "new",
                "to",
                "after",
                "name",
                "status",
            ),
        )
        if value:
            return value
    return None


def _status_name_from_record(record: Mapping[str, Any]) -> str | None:
    for key in ("status", "state", "workflowState", "workflow_state"):
        value = record.get(key)
        if isinstance(value, str):
            stripped = value.strip()
            if stripped:
                return stripped
        if isinstance(value, Mapping):
            name = _first_string(value, ("name", "title", "status"))
            if name:
                return name
    return None


def _extract_issue_id(records: list[Mapping[str, Any]]) -> str | None:
    for record in records:
        value = _first_string(record, ("issueId", "issue_id", "identifier", "key"))
        if value:
            return value

    for record in records:
        if not _looks_like_issue_record(record):
            continue
        value = _first_string(record, ("id",))
        if value:
            return value
    return None


def _extract_title(records: list[Mapping[str, Any]]) -> str | None:
    for record in records:
        value = _first_string(record, ("title",))
        if value:
            return value
    return None


def _looks_like_issue_record(record: Mapping[str, Any]) -> bool:
    if _normalize_text(record.get("type")) == "issue":
        return True
    return any(key in record for key in ("title", "status", "state", "workflowState"))


def _first_string(record: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = record.get(key)
        if isinstance(value, str):
            stripped = value.strip()
            if stripped:
                return stripped
    return None


def _is_status_field(value: Any) -> bool:
    return _normalize_text(value) in STATUS_FIELD_NAMES


def _normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    spaced = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", value)
    normalized = re.sub(r"[^a-z0-9]+", " ", spaced.lower())
    return " ".join(normalized.split())


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
