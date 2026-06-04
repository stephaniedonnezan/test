"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow_state"}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title-update action when a Linear issue moves to research.

    The Cursor automation payload is flat under ``triggerContext``, while Linear
    webhook payloads can nest the issue under ``data.issue``. This function
    accepts both shapes and returns a small action object for the automation
    layer to apply.
    """

    if not isinstance(event, Mapping):
        return None

    records = _priority_records(event)
    if not _is_status_change(records):
        return None

    if not _status_is_to_research(records):
        return None

    issue_id = _first_text(records, ("id", "issueId", "issue_id", "identifier", "key"))
    title = _first_text(records, ("title", "issueTitle", "issue_title"))
    if issue_id is None or title is None:
        return None

    if title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _priority_records(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return useful mappings with outer trigger metadata before nested issue data."""

    records: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and not any(value is record for record in records):
            records.append(value)

    add(event.get("triggerContext"))
    add(event)

    for container_key in ("data", "payload", "webhook", "issue"):
        container = event.get(container_key)
        add(container)
        if isinstance(container, Mapping):
            for issue_key in ("issue", "node", "data"):
                add(container.get(issue_key))

    for record in _walk_mappings(event):
        add(record)

    return records


def _walk_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for child in value.values():
            yield from _walk_mappings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_mappings(child)


def _is_status_change(records: list[Mapping[str, Any]]) -> bool:
    trigger_tokens = {
        _normalize_token(value)
        for record in records
        for key in ("trigger", "webhookType", "webhook_type", "action", "type", "event", "eventType")
        if (value := record.get(key)) is not None
    }

    if trigger_tokens & {"statuschanged", "statuschange", "statechanged", "workflowstatechanged"}:
        return True

    issue_update_tokens = {"issueupdated", "updatedissue", "update", "updated"}
    return bool(trigger_tokens & issue_update_tokens) and _has_status_field_change(records)


def _has_status_field_change(records: list[Mapping[str, Any]]) -> bool:
    for record in records:
        updated_fields = record.get("updatedFields") or record.get("updated_fields")
        if _contains_status_field(updated_fields):
            return True

        changes = record.get("changes") or record.get("changed") or record.get("change")
        if isinstance(changes, Mapping):
            if any(_normalize_token(key) in STATUS_FIELD_NAMES for key in changes):
                return True
            if _contains_status_field(changes.get("fields")):
                return True
        elif _contains_status_field(changes):
            return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_token(value) in STATUS_FIELD_NAMES

    if isinstance(value, Mapping):
        return any(_normalize_token(key) in STATUS_FIELD_NAMES for key in value)

    if isinstance(value, list):
        return any(_contains_status_field(item) for item in value)

    return False


def _status_is_to_research(records: list[Mapping[str, Any]]) -> bool:
    return any(_normalize_status(value) == TARGET_STATUS for value in _status_values(records))


def _status_values(records: list[Mapping[str, Any]]) -> Iterable[Any]:
    explicit_keys = (
        "newStatus",
        "new_status",
        "toStatus",
        "to_status",
        "statusName",
        "status_name",
        "stateName",
        "state_name",
        "workflowStateName",
        "workflow_state_name",
    )
    fallback_keys = ("status", "state", "workflowState", "workflow_state")

    for record in records:
        for key in explicit_keys:
            if key in record:
                yield from _extract_named_values(record[key])

    for record in records:
        changes = record.get("changes") or record.get("changed") or record.get("change")
        if isinstance(changes, Mapping):
            for key in fallback_keys:
                if key in changes:
                    yield from _extract_change_destination(changes[key])

    for record in records:
        for key in fallback_keys:
            if key in record:
                yield from _extract_named_values(record[key])


def _extract_change_destination(value: Any) -> Iterable[Any]:
    if isinstance(value, Mapping):
        for key in ("to", "after", "new", "current", "name"):
            if key in value:
                yield from _extract_named_values(value[key])
    else:
        yield from _extract_named_values(value)


def _extract_named_values(value: Any) -> Iterable[Any]:
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            if key in value:
                yield value[key]
    else:
        yield value


def _first_text(records: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for record in records:
        for key in keys:
            value = record.get(key)
            if isinstance(value, str):
                stripped = value.strip()
                if stripped:
                    return stripped
    return None


def _normalize_status(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return re.sub(r"[^a-z0-9]+", " ", spaced.lower()).strip()


def _normalize_token(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    return re.sub(r"[^a-z0-9]+", "", value.lower())


def main() -> int:
    payload = json.load(sys.stdin)
    result = build_issue_title_update(payload)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
