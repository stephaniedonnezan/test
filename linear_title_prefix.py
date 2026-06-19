"""Build Linear issue title updates for Cursor research status automation."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}
STATUS_CHANGE_TRIGGERS = {
    "statuschanged",
    "statuschange",
    "statusupdated",
    "statusupdate",
    "statechanged",
    "statechange",
    "workflowstatechanged",
    "workflowstatechange",
}
GENERIC_UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issueupdate",
    "issueupdated",
    "updatedissue",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear issue title update action when the event enters research."""

    if not isinstance(event, Mapping):
        return None

    payload = _merged_payload(event)
    if not _is_status_change_event(payload):
        return None

    status = _status_name(payload)
    if _normalize_status(status) != _normalize_status(TARGET_STATUS):
        return None

    issue_id = _first_text(payload, ("issueId", "issue_id", "id", "identifier", "key"))
    title = _first_text(payload, ("title", "name"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _merged_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten common Cursor and Linear wrappers while preserving top-level metadata."""

    merged: dict[str, Any] = {}

    for key in ("triggerContext", "data", "issue"):
        value = event.get(key)
        if isinstance(value, Mapping):
            merged.update(_merged_payload(value))

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        merged.update(_merged_payload(issue))

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            merged.update(_merged_payload(issue))

    merged.update(event)
    return merged


def _is_status_change_event(payload: Mapping[str, Any]) -> bool:
    trigger_values = [
        payload.get("trigger"),
        payload.get("webhookType"),
        payload.get("action"),
        payload.get("type"),
    ]
    normalized = {_normalize_token(value) for value in trigger_values if value}

    if normalized & STATUS_CHANGE_TRIGGERS:
        return True

    if normalized & GENERIC_UPDATE_TRIGGERS:
        return _updated_fields_include_status(payload)

    return False


def _updated_fields_include_status(payload: Mapping[str, Any]) -> bool:
    updated_fields = payload.get("updatedFields") or payload.get("updated_fields")
    if _field_list_includes_status(updated_fields):
        return True

    changes = payload.get("changes") or payload.get("changedFields")
    if isinstance(changes, Mapping):
        return any(_normalize_field(key) in STATUS_FIELDS for key in changes)
    if isinstance(changes, list):
        return any(_change_item_is_status(item) for item in changes)

    return False


def _field_list_includes_status(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_field(value) in STATUS_FIELDS
    if isinstance(value, list | tuple | set):
        return any(_field_list_includes_status(item) for item in value)
    if isinstance(value, Mapping):
        return any(_normalize_field(key) in STATUS_FIELDS for key in value)
    return False


def _change_item_is_status(item: Any) -> bool:
    if isinstance(item, str):
        return _normalize_field(item) in STATUS_FIELDS
    if isinstance(item, Mapping):
        field = _first_text(item, ("field", "name", "key", "property"))
        return _normalize_field(field) in STATUS_FIELDS if field else False
    return False


def _status_name(payload: Mapping[str, Any]) -> str | None:
    for key in (
        "newStatus",
        "new_status",
        "statusName",
        "status_name",
        "newState",
        "new_state",
        "workflowState",
        "workflow_state",
        "state",
        "status",
    ):
        value = payload.get(key)
        text = _text_or_name(value)
        if text:
            return text

    changes = payload.get("changes") or payload.get("changedFields")
    if isinstance(changes, Mapping):
        for key, value in changes.items():
            if _normalize_field(key) in STATUS_FIELDS:
                text = _changed_value_text(value)
                if text:
                    return text
    elif isinstance(changes, list):
        for item in changes:
            if isinstance(item, Mapping) and _change_item_is_status(item):
                text = _changed_value_text(item)
                if text:
                    return text

    return None


def _changed_value_text(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("newValue", "new_value", "to", "after", "value", "name"):
            text = _text_or_name(value.get(key))
            if text:
                return text
    return _text_or_name(value)


def _text_or_name(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, Mapping):
        return _first_text(value, ("name", "title", "label"))
    return None


def _first_text(payload: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _has_prefix(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())


def _normalize_status(value: str | None) -> str | None:
    if value is None:
        return None
    return _normalize_token(value)


def _normalize_token(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    value = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", value)
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def _normalize_field(value: Any) -> str:
    return _normalize_token(value)


def main() -> int:
    payload = json.load(sys.stdin)
    update = build_issue_title_update(payload)
    if update is None:
        return 0
    json.dump(update, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
