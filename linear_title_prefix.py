"""Build Linear issue-title update actions for research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


CURSOR_RESEARCHING_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
TITLE_SEPARATOR = ": "
STATUS_FIELDS = {"status", "state", "workflowstate", "workflowstatus"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title-update action when a Linear issue moves to to research."""
    if not isinstance(event, Mapping):
        return None

    payload = _flatten_payload(event)
    if not _is_status_change_event(payload):
        return None

    status = _extract_status(payload)
    if _normalize_text(status) != TARGET_STATUS:
        return None

    issue_id = _extract_text(payload, ("issueId", "issue_id", "id", "identifier"))
    title = _extract_text(payload, ("title",))
    if not issue_id or not title:
        return None

    if _has_cursor_researching_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{CURSOR_RESEARCHING_PREFIX}{TITLE_SEPARATOR}{title}",
    }


def _flatten_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key in ("data", "issue", "triggerContext"):
        nested = event.get(key)
        if isinstance(nested, Mapping):
            payload.update(_flatten_payload(nested))
    payload.update(event)
    return payload


def _is_status_change_event(payload: Mapping[str, Any]) -> bool:
    trigger_values = (
        payload.get("trigger"),
        payload.get("webhookType"),
        payload.get("action"),
        payload.get("type"),
    )
    normalized_triggers = {_normalize_text(value) for value in trigger_values if value}
    if normalized_triggers & {"status changed", "status change", "status updated"}:
        return True

    updated_fields = _updated_fields(payload.get("updatedFields") or payload.get("updated_fields"))
    if normalized_triggers & {"update", "updated", "issue updated", "updated issue"}:
        return bool(updated_fields & STATUS_FIELDS)

    return False


def _extract_status(payload: Mapping[str, Any]) -> str | None:
    for key in ("newStatus", "new_status", "status"):
        value = payload.get(key)
        text = _text_or_name(value)
        if text:
            return text

    for key in ("state", "workflowState", "workflowStatus"):
        text = _text_or_name(payload.get(key))
        if text:
            return text

    return None


def _extract_text(payload: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str):
            text = value.strip()
            if text:
                return text
    return None


def _text_or_name(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, Mapping):
        name = value.get("name") or value.get("title")
        if isinstance(name, str):
            return name.strip() or None
    return None


def _updated_fields(value: Any) -> set[str]:
    if isinstance(value, str):
        return {_normalize_key(value)}
    if isinstance(value, Mapping):
        return {_normalize_key(key) for key in value}
    if isinstance(value, (list, tuple, set)):
        return {_normalize_key(item) for item in value if isinstance(item, str)}
    return set()


def _normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return re.sub(r"[\s_-]+", " ", spaced).strip().lower()


def _normalize_key(value: str) -> str:
    return re.sub(r"[\s_-]+", "", value).strip().lower()


def _has_cursor_researching_prefix(title: str) -> bool:
    normalized_title = title.strip().lower()
    return normalized_title.startswith(CURSOR_RESEARCHING_PREFIX.lower())


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
