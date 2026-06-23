"""Build Linear issue title updates for research status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


RESEARCH_STATUS = "to research"
TITLE_PREFIX = "Cursor researching"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}
STATUS_CHANGE_TRIGGERS = {"statuschanged", "statuschange"}
GENERIC_UPDATE_TRIGGERS = {"update", "issueupdate", "issueupdated", "updatedissue"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue-title update action when a Linear issue enters research."""

    if not isinstance(event, Mapping):
        return None

    flattened = _flatten_event(event)
    if not _is_status_change(flattened):
        return None

    status = _extract_status(flattened)
    if _normalize_text(status) != RESEARCH_STATUS:
        return None

    title = _string_value(_first_present(flattened, ("title", "name")))
    issue_id = _extract_issue_id(event, flattened)
    if not title or not issue_id:
        return None

    if title.lower().startswith(TITLE_PREFIX.lower()):
        new_title = title
    else:
        new_title = f"{TITLE_PREFIX}: {title}"

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": new_title,
    }


def _flatten_event(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common Linear/Cursor nesting shapes while preserving outer metadata."""

    flattened: dict[str, Any] = {}

    for key in ("issue", "data", "triggerContext", "automation_trigger_info"):
        nested = event.get(key)
        if isinstance(nested, Mapping):
            flattened.update(_flatten_event(nested))

    flattened.update(event)
    return flattened


def _extract_issue_id(
    event: Mapping[str, Any], flattened: Mapping[str, Any]
) -> str | None:
    for nested_issue in _issue_mappings(event):
        issue_id = _string_value(
            _first_present(nested_issue, ("issueId", "issue_id", "identifier", "key", "id"))
        )
        if issue_id:
            return issue_id

    return _string_value(
        _first_present(flattened, ("issueId", "issue_id", "identifier", "key", "id"))
    )


def _issue_mappings(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    automation_trigger_info = event.get("automation_trigger_info")
    if isinstance(automation_trigger_info, Mapping):
        yield from _issue_mappings(automation_trigger_info)

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        yield trigger_context

    data = event.get("data")
    if isinstance(data, Mapping):
        data_issue = data.get("issue")
        if isinstance(data_issue, Mapping):
            yield data_issue
        yield data

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        yield issue


def _is_status_change(event: Mapping[str, Any]) -> bool:
    trigger_values = [
        _normalize_key(value)
        for key in ("trigger", "webhookType", "action", "type")
        if (value := event.get(key)) is not None
    ]

    if any(value in STATUS_CHANGE_TRIGGERS for value in trigger_values):
        return True

    if any(value in GENERIC_UPDATE_TRIGGERS for value in trigger_values):
        return _updated_fields_include_status(event)

    return False


def _updated_fields_include_status(event: Mapping[str, Any]) -> bool:
    updated_fields = event.get("updatedFields")
    if _field_names_include_status(updated_fields):
        return True

    changes = event.get("changes")
    if isinstance(changes, Mapping):
        return any(_normalize_key(key) in STATUS_FIELDS for key in changes)
    if isinstance(changes, Iterable) and not isinstance(changes, (str, bytes)):
        return any(_change_item_is_status(item) for item in changes)

    return False


def _field_names_include_status(fields: Any) -> bool:
    if isinstance(fields, str):
        return _normalize_key(fields) in STATUS_FIELDS

    if isinstance(fields, Iterable) and not isinstance(fields, (str, bytes, Mapping)):
        return any(_normalize_key(field) in STATUS_FIELDS for field in fields)

    return False


def _change_item_is_status(item: Any) -> bool:
    if isinstance(item, str):
        return _normalize_key(item) in STATUS_FIELDS

    if isinstance(item, Mapping):
        field = _first_present(item, ("field", "name", "key", "path"))
        return _normalize_key(field) in STATUS_FIELDS

    return False


def _extract_status(event: Mapping[str, Any]) -> str | None:
    for key in ("newStatus", "new_status", "toStatus", "status", "state", "workflowState"):
        value = event.get(key)
        status = _status_name(value)
        if status:
            return status

    changes = event.get("changes")
    if isinstance(changes, Mapping):
        for key, value in changes.items():
            if _normalize_key(key) in STATUS_FIELDS:
                status = _changed_status_value(value)
                if status:
                    return status

    if isinstance(changes, Iterable) and not isinstance(changes, (str, bytes)):
        for item in changes:
            if not _change_item_is_status(item):
                continue
            status = _changed_status_value(item)
            if status:
                return status

    return None


def _changed_status_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("newValue", "new_value", "to", "after", "value", "name"):
            status = _status_name(value.get(key))
            if status:
                return status

    return _status_name(value)


def _status_name(value: Any) -> str | None:
    if isinstance(value, Mapping):
        return _string_value(
            _first_present(value, ("name", "label", "title", "value", "id"))
        )

    return _string_value(value)


def _first_present(mapping: Mapping[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        value = mapping.get(key)
        if value is not None:
            return value
    return None


def _string_value(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _normalize_text(value: Any) -> str:
    string = _string_value(value)
    if not string:
        return ""

    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", string)
    return re.sub(r"[\s_-]+", " ", spaced).strip().lower()


def _normalize_key(value: Any) -> str:
    string = _string_value(value)
    if not string:
        return ""

    return re.sub(r"[\s_\-:.]+", "", string).lower()


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        json.dump(update, sys.stdout)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
