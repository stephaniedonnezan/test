"""Build Linear issue title updates for research-status automations."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "stateid", "workflowstate", "workflowstateid"}
EXPLICIT_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "status",
    "state",
    "workflowState",
)


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to To Research."""
    if not isinstance(event, Mapping):
        return None

    payload = _merge_payload(event)
    if not _is_status_change_event(payload):
        return None

    status = _extract_new_status(payload)
    if _normalize_status(status) != TARGET_STATUS:
        return None

    issue_id = _first_text(payload, ("id", "issueId", "issue_id", "identifier"))
    title = _first_text(payload, ("title", "name"))
    if not issue_id or not title:
        return None

    trimmed_title = title.strip()
    if _has_prefix(trimmed_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {trimmed_title}",
    }


def _merge_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten common Cursor automation and Linear webhook shapes."""
    merged: dict[str, Any] = {}

    for key in ("data", "issue"):
        value = event.get(key)
        if isinstance(value, Mapping):
            merged.update(_merge_payload(value))

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        merged.update(_merge_payload(trigger_context))

    for key, value in event.items():
        if key not in {"data", "issue", "triggerContext"}:
            merged[key] = value

    return merged


def _is_status_change_event(payload: Mapping[str, Any]) -> bool:
    trigger_values = [
        payload.get(key)
        for key in ("trigger", "event", "action", "type", "webhookType")
        if payload.get(key) is not None
    ]
    normalized_triggers = {_normalize_event(value) for value in trigger_values}

    if "status changed" in normalized_triggers or "status change" in normalized_triggers:
        return True

    updated_fields = _updated_fields(payload.get("updatedFields"))
    if not updated_fields:
        updated_fields = _updated_fields(payload.get("updated_fields"))

    if updated_fields and normalized_triggers & {"update", "issue updated", "updated issue"}:
        return bool(updated_fields & STATUS_FIELDS)

    updated_from = payload.get("updatedFrom") or payload.get("updated_from")
    if isinstance(updated_from, Mapping) and normalized_triggers & {"update", "issue"}:
        return bool({_normalize_field_name(key) for key in updated_from} & STATUS_FIELDS)

    return False


def _extract_new_status(payload: Mapping[str, Any]) -> Any:
    for key in EXPLICIT_STATUS_KEYS:
        value = payload.get(key)
        status = _status_name(value)
        if status:
            return status
    return None


def _status_name(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            nested = value.get(key)
            if isinstance(nested, str):
                return nested
    return None


def _updated_fields(value: Any) -> set[str]:
    if isinstance(value, str):
        return {_normalize_field_name(value)}
    if isinstance(value, Mapping):
        return {_normalize_field_name(key) for key in value}
    if isinstance(value, list | tuple | set):
        fields: set[str] = set()
        for item in value:
            if isinstance(item, str):
                fields.add(_normalize_field_name(item))
            elif isinstance(item, Mapping):
                fields.update(_normalize_field_name(key) for key in item)
        return fields
    return set()


def _first_text(payload: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _has_prefix(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())


def _normalize_status(value: Any) -> str | None:
    text = _status_name(value)
    if text is None:
        return None
    return _normalize_words(text)


def _normalize_event(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return _normalize_words(value)


def _normalize_field_name(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^a-z0-9]", "", _split_camel(value).casefold())


def _normalize_words(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[_\-]+", " ", _split_camel(value)).strip().casefold())


def _split_camel(value: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
