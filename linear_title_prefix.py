"""Build title update actions for Linear issue research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow status"}
TRIGGER_FIELDS = ("trigger", "webhookType", "action", "type")
EXPLICIT_STATUS_FIELDS = (
    "newStatus",
    "new_status",
    "status",
    "state",
    "workflowState",
    "workflow_status",
)


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue-title update action when a Linear issue moves to research."""

    if not isinstance(event, Mapping):
        return None

    payload = _flatten_event(event)
    if not _is_status_change_event(payload):
        return None

    status = _extract_status(payload)
    if _normalize(status) != TARGET_STATUS:
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
        "title": f"{TITLE_PREFIX}: {title.strip()}",
    }


def _flatten_event(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common automation and Linear webhook nesting into one lookup map."""

    payload: dict[str, Any] = {}

    def merge(value: Any) -> None:
        if not isinstance(value, Mapping):
            return

        # Issue data is less specific than outer trigger metadata, so merge it first.
        for nested_key in ("issue", "data"):
            nested = value.get(nested_key)
            if isinstance(nested, Mapping):
                merge(nested)

        for key, item in value.items():
            if key not in {"issue", "data", "triggerContext"}:
                payload[key] = item

        trigger_context = value.get("triggerContext")
        if isinstance(trigger_context, Mapping):
            merge(trigger_context)

    merge(event)
    return payload


def _is_status_change_event(payload: Mapping[str, Any]) -> bool:
    trigger_values = [
        str(payload[key])
        for key in TRIGGER_FIELDS
        if key in payload and payload[key] is not None
    ]

    if any(_normalize(value) == "status changed" for value in trigger_values):
        return True

    if not any(_normalize(value) in {"issue updated", "updated issue", "update"} for value in trigger_values):
        return False

    updated_fields = payload.get("updatedFields") or payload.get("updated_fields")
    return _contains_status_field(updated_fields)


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize(value) in STATUS_FIELDS
    if isinstance(value, Mapping):
        return any(_normalize(key) in STATUS_FIELDS for key in value)
    if isinstance(value, list | tuple | set):
        return any(_contains_status_field(item) for item in value)
    return False


def _extract_status(payload: Mapping[str, Any]) -> str | None:
    for key in EXPLICIT_STATUS_FIELDS:
        if key in payload:
            value = _text_or_name(payload[key])
            if value:
                return value
    return None


def _first_text(payload: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        if key in payload:
            value = _text_or_name(payload[key])
            if value:
                return value.strip()
    return None


def _text_or_name(value: Any) -> str | None:
    if isinstance(value, str):
        text = value.strip()
        return text or None
    if isinstance(value, Mapping):
        for key in ("name", "title", "id", "identifier"):
            nested = value.get(key)
            if isinstance(nested, str) and nested.strip():
                return nested.strip()
    return None


def _normalize(value: Any) -> str:
    text = str(value)
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[_\-\s]+", " ", text)
    return text.strip().casefold()


def _has_prefix(title: str) -> bool:
    return title.lstrip().casefold().startswith(TITLE_PREFIX.casefold())


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
