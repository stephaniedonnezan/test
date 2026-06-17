"""Build Linear issue title updates for Cursor research-status automations."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {
    "status",
    "statusid",
    "status_id",
    "state",
    "stateid",
    "state_id",
    "workflowstate",
    "workflow_state",
    "workflowstateid",
    "workflow_state_id",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to To Research."""
    if not isinstance(event, Mapping):
        return None

    payload = _event_payload(event)
    if not _is_status_change_event(payload):
        return None

    new_status = _status_name(_first_present(payload, ("newStatus", "new_status", "status", "state", "workflowState", "workflow_state")))
    if _normalize_status(new_status) != TARGET_STATUS:
        return None

    issue_id = _clean_text(_first_present(payload, ("identifier", "key", "issueId", "issue_id", "id")))
    title = _clean_text(_first_present(payload, ("title", "name")))
    if not issue_id or not title or _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _event_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten common Cursor and Linear webhook envelopes into one lookup map."""
    payload: dict[str, Any] = {}

    for container in _mappings_at(event, ("data", "issue", "triggerContext")):
        payload.update(container)

    # Preserve outer webhook metadata when it would otherwise be hidden by issue data.
    for key in ("trigger", "webhookType", "action", "type", "updatedFields", "changes", "updatedFrom", "newStatus", "new_status"):
        if key in event:
            payload[key] = event[key]

    return payload


def _mappings_at(value: Any, preferred_keys: Iterable[str]) -> list[Mapping[str, Any]]:
    if not isinstance(value, Mapping):
        return []

    mappings: list[Mapping[str, Any]] = [value]
    for key in preferred_keys:
        nested = value.get(key)
        if isinstance(nested, Mapping):
            mappings.extend(_mappings_at(nested, preferred_keys))
    return mappings


def _is_status_change_event(payload: Mapping[str, Any]) -> bool:
    event_names = [
        _clean_text(payload.get(key))
        for key in ("trigger", "webhookType", "action", "type")
        if payload.get(key) is not None
    ]

    if any(_normalized_event_name(name) in {"statuschanged", "statechanged", "workflowstatechanged"} for name in event_names):
        return True

    if any(_normalized_event_name(name) in {"update", "updated", "issueupdate", "issueupdated", "updatedissue"} for name in event_names):
        return _changed_fields_include_status(payload)

    return False


def _changed_fields_include_status(payload: Mapping[str, Any]) -> bool:
    updated_fields = payload.get("updatedFields")
    if isinstance(updated_fields, str):
        if _normalize_field(updated_fields) in STATUS_FIELDS:
            return True
    elif isinstance(updated_fields, Iterable) and not isinstance(updated_fields, (bytes, bytearray, Mapping)):
        for field in updated_fields:
            if _normalize_field(field) in STATUS_FIELDS:
                return True

    for key in ("changes", "updatedFrom"):
        changes = payload.get(key)
        if isinstance(changes, Mapping) and any(_normalize_field(field) in STATUS_FIELDS for field in changes):
            return True

    return False


def _first_present(payload: Mapping[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        value = payload.get(key)
        if value is not None:
            return value
    return None


def _status_name(value: Any) -> str | None:
    if isinstance(value, Mapping):
        return _clean_text(_first_present(value, ("name", "title", "status", "state")))
    return _clean_text(value)


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def _normalized_event_name(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"[^a-z0-9]", "", _split_camel(value).lower())


def _normalize_status(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", _split_camel(value).lower())).strip()


def _normalize_field(value: Any) -> str:
    return re.sub(r"[^a-z0-9_]", "", _split_camel(str(value)).replace(" ", "_").lower())


def _split_camel(value: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        json.dump(action, sys.stdout)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
