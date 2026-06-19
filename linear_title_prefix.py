"""Build Linear issue title updates for research-status automations."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue-title update action when a Linear issue enters research."""
    if not isinstance(event, Mapping):
        return None

    payload = _flatten_payload(event)
    if not _is_status_change_event(payload):
        return None

    new_status = _extract_new_status(payload)
    if _normalize_words(new_status) != _normalize_words(TARGET_STATUS):
        return None

    issue_id = _first_text(payload, ("issueId", "issue_id", "id", "identifier", "key"))
    title = _first_text(payload, ("title", "name"))
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


def _flatten_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}

    def merge(mapping: Mapping[str, Any]) -> None:
        for key, value in mapping.items():
            if key in {"triggerContext", "data", "issue"} and isinstance(value, Mapping):
                merge(value)
                continue
            payload[key] = value

            if key in {"state", "status", "workflowState", "workflow_state"} and isinstance(value, Mapping):
                name = _text(value.get("name"))
                if name:
                    payload.setdefault(f"{key}Name", name)

    merge(event)
    return payload


def _is_status_change_event(payload: Mapping[str, Any]) -> bool:
    event_names = [
        _text(payload.get(key))
        for key in ("trigger", "webhookType", "action", "type")
        if _text(payload.get(key))
    ]
    normalized_names = {_normalize_identifier(name) for name in event_names}

    if any(name in {"statuschanged", "statuschange"} for name in normalized_names):
        return True
    if "status_changed" in event_names:
        return True

    if any(name in {"issueupdated", "updatedissue", "update", "updated"} for name in normalized_names):
        return _updated_status_fields(payload)

    return False


def _updated_status_fields(payload: Mapping[str, Any]) -> bool:
    updated = payload.get("updatedFields") or payload.get("updated_fields")
    changed_fields = _field_names(updated)

    changes = payload.get("changes") or payload.get("changedFields") or payload.get("changed_fields")
    changed_fields.update(_field_names(changes))

    return bool(changed_fields & STATUS_FIELDS)


def _field_names(value: Any) -> set[str]:
    if isinstance(value, str):
        return {_normalize_identifier(value)}
    if isinstance(value, Mapping):
        return {_normalize_identifier(str(key)) for key in value}
    if isinstance(value, list | tuple | set):
        return {
            normalized
            for item in value
            for normalized in _field_names(item)
            if normalized
        }
    return set()


def _extract_new_status(payload: Mapping[str, Any]) -> str | None:
    for key in (
        "newStatus",
        "new_status",
        "statusName",
        "stateName",
        "workflowStateName",
        "workflow_stateName",
        "status",
        "state",
        "workflowState",
        "workflow_state",
    ):
        value = payload.get(key)
        if isinstance(value, Mapping):
            value = value.get("name")
        text = _text(value)
        if text:
            return text
    return None


def _first_text(payload: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        text = _text(payload.get(key))
        if text:
            return text
    return None


def _has_prefix(title: str) -> bool:
    return title.strip().lower().startswith(PREFIX.lower())


def _text(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _normalize_words(value: str | None) -> str | None:
    if value is None:
        return None
    return _normalize_identifier(_split_camel_case(value))


def _normalize_identifier(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


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
