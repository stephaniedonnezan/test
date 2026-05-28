"""Build Linear issue title updates for To Research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflowstate",
    "workflowstatus",
    "workflow",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to To Research."""
    if not isinstance(event, Mapping):
        return None

    payload = _flatten_event(event)
    if not _is_status_change_event(payload):
        return None

    status = _new_status(payload)
    if _normalize_words(status) != TARGET_STATUS:
        return None

    issue_id = _first_text(payload, ("issueId", "issue_id", "id", "identifier"))
    title = _first_text(payload, ("title", "name"))
    if not issue_id or not title:
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": title if _has_prefix(title) else f"{PREFIX}: {title}",
    }


def _flatten_event(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common Cursor and Linear webhook envelopes into one payload view."""
    flattened: dict[str, Any] = {}

    def merge(value: Any) -> None:
        if not isinstance(value, Mapping):
            return

        data = value.get("data")
        if isinstance(data, Mapping):
            merge(data)

        issue = value.get("issue")
        if isinstance(issue, Mapping):
            merge(issue)

        trigger_context = value.get("triggerContext")
        if isinstance(trigger_context, Mapping):
            merge(trigger_context)

        flattened.update(value)

    merge(event)
    return flattened


def _is_status_change_event(payload: Mapping[str, Any]) -> bool:
    trigger_values = [
        payload.get("trigger"),
        payload.get("webhookType"),
        payload.get("action"),
        payload.get("type"),
    ]
    normalized_triggers = {_normalize_words(value) for value in trigger_values}

    if "status changed" in normalized_triggers:
        return True

    updated_fields = payload.get("updatedFields") or payload.get("updated_fields")
    if _updated_fields_include_status(updated_fields):
        return True

    updated_from = payload.get("updatedFrom") or payload.get("updated_from")
    return _updated_from_includes_status(updated_from)


def _updated_fields_include_status(fields: Any) -> bool:
    if isinstance(fields, str):
        fields = [fields]

    if not isinstance(fields, list | tuple | set):
        return False

    return any(_status_field_name(field) in STATUS_FIELD_NAMES for field in fields)


def _updated_from_includes_status(updated_from: Any) -> bool:
    if not isinstance(updated_from, Mapping):
        return False

    return any(_status_field_name(field) in STATUS_FIELD_NAMES for field in updated_from)


def _new_status(payload: Mapping[str, Any]) -> str | None:
    for key in ("newStatus", "new_status", "status"):
        value = _field_text(payload.get(key))
        if value:
            return value

    for key in ("state", "workflowState", "workflow_status", "workflowStatus"):
        value = _field_text(payload.get(key))
        if value:
            return value

    return None


def _first_text(payload: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = _field_text(payload.get(key))
        if value:
            return value
    return None


def _field_text(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "id", "identifier"):
            text = _field_text(value.get(key))
            if text:
                return text

    return None


def _has_prefix(title: str) -> bool:
    return bool(re.match(r"^\s*cursor researching\b", title, re.IGNORECASE))


def _status_field_name(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", _normalize_words(value))


def _normalize_words(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value.strip())
    words = re.sub(r"[^A-Za-z0-9]+", " ", spaced)
    return " ".join(words.casefold().split())


def main() -> int:
    action = build_issue_title_update(json.load(sys.stdin))
    if action is not None:
        print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
