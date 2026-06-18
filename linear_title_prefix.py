"""Build Linear issue title updates for Cursor research automation."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear issue title update when an issue moves to to-research."""
    if not isinstance(event, Mapping):
        return None

    payload = _flatten_event(event)
    if not _is_status_change_event(payload):
        return None

    status = _status_from_payload(payload)
    if _normalize_value(status) != TARGET_STATUS:
        return None

    issue_id = _first_string(payload, ("issueId", "issue_id", "id", "identifier", "key"))
    title = _first_string(payload, ("title", "name"))
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


def _flatten_event(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common Cursor and Linear payload nesting into one lookup table."""
    flattened: dict[str, Any] = {}

    def merge_mapping(value: Any) -> None:
        if isinstance(value, Mapping):
            flattened.update(value)

    merge_mapping(event.get("issue"))
    data = event.get("data")
    if isinstance(data, Mapping):
        merge_mapping(data.get("issue"))
        merge_mapping(data)
    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        merge_mapping(trigger_context.get("issue"))
        merge_mapping(trigger_context)
    merge_mapping(event)

    return flattened


def _is_status_change_event(payload: Mapping[str, Any]) -> bool:
    event_markers = (
        payload.get("trigger"),
        payload.get("webhookType"),
        payload.get("action"),
        payload.get("type"),
    )
    normalized_markers = {_normalize_value(marker) for marker in event_markers if marker}

    if any(marker in {"status changed", "status change", "statusupdated"} for marker in normalized_markers):
        return True

    if any(marker in {"issue updated", "updated issue", "update", "updated"} for marker in normalized_markers):
        return _updated_fields_include_status(payload)

    return False


def _updated_fields_include_status(payload: Mapping[str, Any]) -> bool:
    updated_fields = payload.get("updatedFields") or payload.get("updated_fields")
    if isinstance(updated_fields, str):
        fields = [updated_fields]
    elif isinstance(updated_fields, list | tuple | set):
        fields = updated_fields
    else:
        fields = []

    for field in fields:
        if _normalize_field_name(field) in STATUS_FIELDS:
            return True

    changes = payload.get("changes")
    if isinstance(changes, Mapping):
        return any(_normalize_field_name(field) in STATUS_FIELDS for field in changes)

    return False


def _status_from_payload(payload: Mapping[str, Any]) -> str | None:
    for key in ("newStatus", "new_status", "toStatus", "to_status"):
        value = payload.get(key)
        if isinstance(value, str):
            return value
        if isinstance(value, Mapping):
            name = value.get("name")
            if isinstance(name, str):
                return name

    for key in ("status", "state", "workflowState", "workflow_state"):
        value = payload.get(key)
        if isinstance(value, str):
            return value
        if isinstance(value, Mapping):
            name = value.get("name")
            if isinstance(name, str):
                return name

    changes = payload.get("changes")
    if isinstance(changes, Mapping):
        for key in ("status", "state", "workflowState", "workflow_state"):
            value = changes.get(key)
            status = _status_from_change(value)
            if status:
                return status

    return None


def _status_from_change(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        for key in ("newValue", "new_value", "to", "after", "name"):
            candidate = value.get(key)
            if isinstance(candidate, str):
                return candidate
            if isinstance(candidate, Mapping):
                name = candidate.get("name")
                if isinstance(name, str):
                    return name
    return None


def _first_string(payload: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _has_prefix(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())


def _normalize_value(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    value = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    value = re.sub(r"[_-]+", " ", value)
    return " ".join(value.casefold().split())


def _normalize_field_name(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^a-z]", "", value.casefold())


def main() -> int:
    """Read a JSON event from stdin and print the title update action if any."""
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
