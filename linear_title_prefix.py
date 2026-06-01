"""Build title updates for Linear issues entering research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELDS = ("status", "state", "workflowState", "workflow_state")
_NEW_STATUS_FIELDS = ("newStatus", "new_status", "toStatus", "to_status")
_ISSUE_ID_FIELDS = ("id", "issueId", "issue_id", "identifier")
_TITLE_FIELDS = ("title", "name")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to research."""
    if not isinstance(event, Mapping):
        return None

    payload = _flatten_payload(event)
    if not _is_status_change_event(payload):
        return None

    status = _extract_new_status(payload)
    if _normalize(status) != TARGET_STATUS:
        return None

    issue_id = _first_text(payload, _ISSUE_ID_FIELDS)
    title = _first_text(payload, _TITLE_FIELDS)
    if not issue_id or not title:
        return None

    if _has_title_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _flatten_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common automation and Linear webhook nesting into one payload."""
    payload: dict[str, Any] = {}

    for key in ("triggerContext", "data", "issue"):
        nested = event.get(key)
        if isinstance(nested, Mapping):
            payload.update(_flatten_payload(nested))

    payload.update(event)
    return payload


def _is_status_change_event(payload: Mapping[str, Any]) -> bool:
    event_markers = [
        payload.get("trigger"),
        payload.get("webhookType"),
        payload.get("action"),
        payload.get("type"),
    ]
    normalized_markers = {_normalize(marker) for marker in event_markers if marker}

    if "status changed" in normalized_markers or "status change" in normalized_markers:
        return True

    issue_update_markers = {"update", "updated", "issue updated", "updated issue"}
    if normalized_markers & issue_update_markers:
        return _updated_fields_include_status(payload.get("updatedFields"))

    return False


def _updated_fields_include_status(updated_fields: Any) -> bool:
    if updated_fields is None:
        return False

    fields = updated_fields
    if isinstance(fields, str):
        fields = [fields]

    if not isinstance(fields, list | tuple | set):
        return False

    status_field_names = {_normalize(field) for field in _STATUS_FIELDS}
    return any(_normalize(field) in status_field_names for field in fields)


def _extract_new_status(payload: Mapping[str, Any]) -> str | None:
    explicit_status = _first_text(payload, _NEW_STATUS_FIELDS)
    if explicit_status:
        return explicit_status

    for field in _STATUS_FIELDS:
        value = payload.get(field)
        if isinstance(value, Mapping):
            text = _first_text(value, ("name", "title", "id"))
            if text:
                return text
        elif isinstance(value, str):
            return value.strip()

    return None


def _first_text(payload: Mapping[str, Any], fields: tuple[str, ...]) -> str | None:
    for field in fields:
        value = payload.get(field)
        if isinstance(value, str):
            text = value.strip()
            if text:
                return text
    return None


def _has_title_prefix(title: str) -> bool:
    return title.strip().lower().startswith(TITLE_PREFIX.lower())


def _normalize(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value.strip())
    text = re.sub(r"[_\-]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.casefold()


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
