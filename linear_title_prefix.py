"""Build Linear issue title updates for research-status transitions.

The automation runtime can pass either the compact Cursor trigger context or a
full Linear webhook payload. This module extracts the issue fields we need from
both shapes and returns the title-update action for the caller to execute.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}
TRIGGER_FIELDS = ("trigger", "webhookType", "action", "type")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title-update action when an issue moves to To Research."""

    if not isinstance(event, Mapping):
        return None

    payload = _flatten_payload(event)

    if not _is_status_change_event(payload):
        return None

    if _normalize_status(_extract_status(payload)) != TARGET_STATUS:
        return None

    issue_id = _first_text(payload, ("id", "issueId", "issue_id", "identifier"))
    title = _first_text(payload, ("title", "name"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if not title or _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _flatten_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common wrapper objects so outer trigger metadata wins."""

    flattened: dict[str, Any] = {}
    for key in ("issue", "data", "triggerContext"):
        value = event.get(key)
        if isinstance(value, Mapping):
            flattened.update(_flatten_payload(value))

    for key, value in event.items():
        if key not in {"issue", "data", "triggerContext"}:
            flattened[key] = value

    return flattened


def _is_status_change_event(payload: Mapping[str, Any]) -> bool:
    trigger_values = [
        _normalize_token(value)
        for key in TRIGGER_FIELDS
        if (value := payload.get(key)) is not None
    ]

    if any(value in {"statuschanged", "statuschange", "statusupdated"} for value in trigger_values):
        return True
    if any(value == "statuschanged" for value in _normalized_updated_fields(payload)):
        return True

    is_issue_update = any(
        value in {"update", "updated", "issueupdated", "updatedissue"} for value in trigger_values
    )
    if is_issue_update:
        updated_fields = _normalized_updated_fields(payload)
        return any(field in STATUS_FIELDS for field in updated_fields)

    return any(value == "status_changed" for value in _raw_text_values(payload, TRIGGER_FIELDS))


def _extract_status(payload: Mapping[str, Any]) -> str | None:
    for key in ("newStatus", "new_status"):
        value = _text_or_name(payload.get(key))
        if value:
            return value

    for key in ("status", "state", "workflowState", "workflow_state"):
        value = _text_or_name(payload.get(key))
        if value:
            return value

    return None


def _normalized_updated_fields(payload: Mapping[str, Any]) -> set[str]:
    fields = payload.get("updatedFields") or payload.get("updated_fields") or payload.get("changes")
    if isinstance(fields, Mapping):
        values = fields.keys()
    elif isinstance(fields, (list, tuple, set)):
        values = fields
    elif fields is None:
        values = ()
    else:
        values = (fields,)

    return {_normalize_token(value) for value in values if _text_or_name(value)}


def _first_text(payload: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = _text_or_name(payload.get(key))
        if value:
            return value
    return None


def _text_or_name(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        for key in ("name", "title", "id", "identifier"):
            nested_value = value.get(key)
            if isinstance(nested_value, str):
                return nested_value
    return None


def _raw_text_values(payload: Mapping[str, Any], keys: tuple[str, ...]) -> set[str]:
    return {
        value
        for key in keys
        if isinstance((value := payload.get(key)), str)
    }


def _normalize_status(value: str | None) -> str | None:
    if value is None:
        return None
    return re.sub(r"[\s_-]+", " ", _split_camel_case(value)).strip().lower()


def _normalize_token(value: Any) -> str:
    text = _text_or_name(value) or ""
    return re.sub(r"[^a-z0-9]", "", _split_camel_case(text).lower())


def _split_camel_case(value: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
