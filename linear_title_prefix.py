"""Build Linear issue title updates for Cursor research automation.

The automation receives webhook-like dictionaries from Linear/Cursor and returns
an action dictionary when an issue moves into the "to research" status.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state", "stateid"}
TRIGGER_FIELDS = {"trigger", "triggertype", "webhooktype", "action", "type"}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title-update action when a Linear issue moves to to-research."""

    if not isinstance(event, Mapping):
        return None

    payload = _merge_payload(event)
    if not _is_status_change(event, payload):
        return None

    status = _extract_new_status(event, payload)
    if _normalize_value(status) != _normalize_value(TARGET_STATUS):
        return None

    issue_id = _extract_text(payload, ("id", "issueId", "issue_id", "identifier"))
    title = _extract_text(payload, ("title", "name"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if not title:
        return None
    if title.lower().startswith(TITLE_PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _merge_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten common automation and Linear webhook nesting into one payload."""

    payload: dict[str, Any] = {}
    for key in ("issue", "data", "triggerContext"):
        nested = event.get(key)
        if isinstance(nested, Mapping):
            for nested_key in ("issue", "data"):
                deeper = nested.get(nested_key)
                if isinstance(deeper, Mapping):
                    payload.update(deeper)
            payload.update(nested)
    for key, value in event.items():
        if key in {"id", "identifier", "issueId", "issue_id", "title", "name"} and key in payload:
            continue
        payload[key] = value
    return payload


def _is_status_change(event: Mapping[str, Any], payload: Mapping[str, Any]) -> bool:
    trigger_values = [_normalize_value(value) for value in _collect_values(event, TRIGGER_FIELDS)]
    trigger_values.extend(_normalize_value(value) for value in _collect_values(payload, TRIGGER_FIELDS))
    trigger_values = [value for value in trigger_values if value]

    status_change_values = {
        "status changed",
        "status change",
        "statuschanged",
        "state changed",
        "state change",
        "workflow state changed",
        "workflow state change",
    }
    if any(value in status_change_values for value in trigger_values):
        return True

    is_issue_update = any(value in {"update", "updated", "issue updated", "updated issue"} for value in trigger_values)
    return is_issue_update and _updated_fields_include_status(event, payload)


def _updated_fields_include_status(*mappings: Mapping[str, Any]) -> bool:
    for mapping in mappings:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            fields = mapping.get(key)
            if isinstance(fields, str):
                values = [fields]
            elif isinstance(fields, list | tuple | set):
                values = fields
            else:
                continue

            normalized_fields = {_normalize_key(str(field)) for field in values}
            if normalized_fields & STATUS_FIELDS:
                return True

        updated_from = mapping.get("updatedFrom") or mapping.get("updated_from")
        if isinstance(updated_from, Mapping):
            normalized_keys = {_normalize_key(str(key)) for key in updated_from}
            if normalized_keys & STATUS_FIELDS:
                return True

    return False


def _extract_new_status(event: Mapping[str, Any], payload: Mapping[str, Any]) -> str | None:
    for mapping in (event, payload):
        status = _extract_text(
            mapping,
            (
                "newStatus",
                "new_status",
                "statusName",
                "status_name",
                "newState",
                "new_state",
                "stateName",
                "state_name",
                "workflowStateName",
                "workflow_state_name",
            ),
        )
        if status:
            return status

    for mapping in (payload, event):
        status = _extract_text(mapping, ("status",))
        if status:
            return status
        for key in ("state", "workflowState", "workflow_state", "status"):
            nested = mapping.get(key)
            if isinstance(nested, Mapping):
                status = _extract_text(nested, ("name", "title", "status"))
                if status:
                    return status

    return None


def _extract_text(mapping: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = mapping.get(key)
        if value is None:
            continue
        if isinstance(value, Mapping):
            nested_value = _extract_text(value, ("name", "title", "id", "identifier"))
            if nested_value:
                return nested_value
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _collect_values(value: Any, wanted_keys: set[str]) -> list[Any]:
    values: list[Any] = []
    if isinstance(value, Mapping):
        for key, nested_value in value.items():
            if _normalize_key(str(key)) in wanted_keys:
                values.append(nested_value)
            values.extend(_collect_values(nested_value, wanted_keys))
    elif isinstance(value, list | tuple):
        for item in value:
            values.extend(_collect_values(item, wanted_keys))
    return values


def _normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", _split_camel_case(value).lower())


def _normalize_value(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"[^a-z0-9]+", " ", _split_camel_case(str(value)).lower()).strip()


def _split_camel_case(value: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
