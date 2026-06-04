"""Build Linear issue title updates for research-status automation events."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow status"}
UPDATED_STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when an issue moves to "to research"."""
    if not isinstance(event, Mapping):
        return None

    payload = _flatten_payload(event)
    if not _is_status_change_event(payload):
        return None

    status = _extract_status(payload)
    if _normalize_words(status) != TARGET_STATUS:
        return None

    issue_id = _first_text(payload, ("id", "issueId", "issue_id", "identifier"))
    title = _first_text(payload, ("title", "name"))
    if not issue_id or not title:
        return None

    if _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _flatten_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common Linear/Cursor wrapper objects while preserving outer metadata."""
    flattened: dict[str, Any] = {}

    for key in ("issue", "data", "triggerContext"):
        value = event.get(key)
        if isinstance(value, Mapping):
            flattened.update(_flatten_payload(value))

    flattened.update(event)
    return flattened


def _is_status_change_event(payload: Mapping[str, Any]) -> bool:
    signals = [
        _normalize_token(value)
        for key in ("trigger", "webhookType", "action", "type")
        for value in _iter_text_values(payload.get(key))
    ]

    if any(signal in {"statuschanged", "statuschange", "statusupdated"} for signal in signals):
        return True

    if any(signal in {"statuschanged", "statuschange"} for signal in _normalized_updated_fields(payload)):
        return True

    if any(signal in {"update", "updated", "issueupdated", "updatedissue"} for signal in signals):
        return bool(_normalized_updated_fields(payload) & UPDATED_STATUS_FIELDS)

    return False


def _extract_status(payload: Mapping[str, Any]) -> str | None:
    for key in ("newStatus", "new_status", "statusName", "status_name"):
        value = _text(payload.get(key))
        if value:
            return value

    for key in ("status", "state", "workflowState"):
        value = payload.get(key)
        if isinstance(value, Mapping):
            name = _text(value.get("name"))
            if name:
                return name
        else:
            text = _text(value)
            if text:
                return text

    return None


def _normalized_updated_fields(payload: Mapping[str, Any]) -> set[str]:
    fields: set[str] = set()
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        fields.update(_normalize_field_name(value) for value in _iter_text_values(payload.get(key)))
    return fields


def _first_text(payload: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for key in keys:
        value = _text(payload.get(key))
        if value:
            return value
    return None


def _iter_text_values(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        stripped = value.strip()
        if stripped:
            yield stripped
    elif isinstance(value, Mapping):
        for nested in value.values():
            yield from _iter_text_values(nested)
    elif isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray)):
        for item in value:
            yield from _iter_text_values(item)


def _text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _normalize_words(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", value)
    normalized = re.sub(r"[^a-zA-Z0-9]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip().lower()


def _normalize_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", _normalize_words(value) or "")


def _normalize_field_name(value: str) -> str:
    return (_normalize_words(value) or "").replace(" ", "")


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 2

    update = build_issue_title_update(event)
    if update is None:
        return 1

    print(json.dumps(update, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
