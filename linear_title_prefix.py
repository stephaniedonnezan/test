"""Build Linear issue title updates for research-status automation events."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflowstatus"}
DIRECT_STATUS_TRIGGERS = {
    "status changed",
    "status change",
    "statuschanged",
    "status changed issue",
}
GENERIC_UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to research."""

    if not isinstance(event, Mapping):
        return None

    payload = _flatten_payload(event)
    if not _is_research_status_change(event, payload):
        return None

    issue_id = _first_text(payload, ("issueId", "issue_id", "id", "identifier", "key"))
    title = _first_text(payload, ("title", "name"))
    if not issue_id or not title:
        return None

    if _already_prefixed(title):
        prefixed_title = title
    else:
        prefixed_title = f"{PREFIX}: {title}"

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": prefixed_title,
    }


def _is_research_status_change(
    event: Mapping[str, Any], payload: Mapping[str, Any]
) -> bool:
    trigger_values = [
        _normalize_event_name(value)
        for value in _event_values(event, ("trigger", "webhookType", "action", "type"))
    ]
    direct_status_change = any(
        value in DIRECT_STATUS_TRIGGERS for value in trigger_values if value
    )
    generic_issue_update = any(
        value in GENERIC_UPDATE_TRIGGERS for value in trigger_values if value
    )

    if not direct_status_change and not (
        generic_issue_update and _change_metadata_mentions_status(event)
    ):
        return False

    return _normalize_status(_new_status(event, payload)) == TARGET_STATUS


def _flatten_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common Cursor and Linear webhook nesting into one lookup map."""

    flattened: dict[str, Any] = {}

    def merge(value: Any) -> None:
        if not isinstance(value, Mapping):
            return
        flattened.update(value)
        for key in ("issue", "data", "triggerContext"):
            nested = value.get(key)
            if isinstance(nested, Mapping):
                merge(nested)

    merge(event)
    return flattened


def _event_values(event: Mapping[str, Any], keys: tuple[str, ...]) -> list[Any]:
    values: list[Any] = []

    def collect(value: Any) -> None:
        if not isinstance(value, Mapping):
            return
        for key in keys:
            if key in value:
                values.append(value[key])
        for nested_key in ("triggerContext", "data"):
            collect(value.get(nested_key))

    collect(event)
    return values


def _new_status(event: Mapping[str, Any], payload: Mapping[str, Any]) -> Any:
    for key in (
        "newStatus",
        "new_status",
        "statusName",
        "stateName",
        "workflowStateName",
    ):
        if key in payload:
            return payload[key]

    change_status = _status_from_changes(event)
    if change_status is not None:
        return change_status

    for key in ("status", "state", "workflowState", "workflow_status"):
        value = payload.get(key)
        if isinstance(value, Mapping):
            for name_key in ("name", "title", "status", "state"):
                if name_key in value:
                    return value[name_key]
        elif value is not None:
            return value

    return None


def _status_from_changes(event: Mapping[str, Any]) -> Any:
    for changes in _change_values(event):
        if isinstance(changes, Mapping):
            for key, value in changes.items():
                if _normalize_field_name(key) in STATUS_FIELD_NAMES:
                    if isinstance(value, Mapping):
                        for value_key in (
                            "newValue",
                            "new_value",
                            "to",
                            "after",
                            "name",
                        ):
                            if value_key in value:
                                nested_value = value[value_key]
                                if isinstance(nested_value, Mapping):
                                    return nested_value.get("name")
                                return nested_value
                    return value
        elif isinstance(changes, list):
            for item in changes:
                status = _status_from_change_item(item)
                if status is not None:
                    return status
    return None


def _status_from_change_item(item: Any) -> Any:
    if not isinstance(item, Mapping):
        return None

    field = item.get("field") or item.get("name") or item.get("key")
    if _normalize_field_name(field) not in STATUS_FIELD_NAMES:
        return None

    for key in ("newValue", "new_value", "to", "after", "value"):
        if key in item:
            value = item[key]
            if isinstance(value, Mapping):
                return value.get("name")
            return value
    return None


def _change_metadata_mentions_status(event: Mapping[str, Any]) -> bool:
    for value in _change_values(event):
        if _metadata_value_mentions_status(value):
            return True
    return False


def _change_values(event: Mapping[str, Any]) -> list[Any]:
    values: list[Any] = []

    def collect(value: Any) -> None:
        if not isinstance(value, Mapping):
            return
        for key in ("updatedFields", "updated_fields", "changedFields", "changes"):
            if key in value:
                values.append(value[key])
        for nested_key in ("triggerContext", "data"):
            collect(value.get(nested_key))

    collect(event)
    return values


def _metadata_value_mentions_status(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_field_name(value) in STATUS_FIELD_NAMES
    if isinstance(value, Mapping):
        return any(
            _normalize_field_name(key) in STATUS_FIELD_NAMES
            or _metadata_value_mentions_status(nested)
            for key, nested in value.items()
        )
    if isinstance(value, list):
        return any(_metadata_value_mentions_status(item) for item in value)
    return False


def _first_text(payload: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str):
            stripped = value.strip()
            if stripped:
                return stripped
    return None


def _already_prefixed(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())


def _normalize_event_name(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    spaced = re.sub(r"([a-z])([A-Z])", r"\1 \2", value)
    return re.sub(r"[_\-\s]+", " ", spaced).strip().casefold()


def _normalize_status(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    spaced = re.sub(r"([a-z])([A-Z])", r"\1 \2", value)
    return re.sub(r"[_\-\s]+", " ", spaced).strip().casefold()


def _normalize_field_name(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return re.sub(r"[_\-\s]+", "", value).casefold()


def main() -> int:
    """Read a JSON event from stdin and print the computed action, if any."""

    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
