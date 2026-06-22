"""Build Linear issue title updates for research-status automations.

The Cursor automation runner can provide either a flattened trigger context or
Linear's nested webhook shape. This module keeps the decision pure so callers
can inspect the returned action before applying it through their integration.
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


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return an issue-title update action when an issue moves to research."""

    if not isinstance(event, Mapping):
        return None

    payload = _flatten_event(event)
    if not _is_status_change_event(payload):
        return None

    status = _extract_new_status(payload)
    if _normalize_status(status) != TARGET_STATUS:
        return None

    issue_id = _first_text(payload, ("issueId", "issue_id", "id", "identifier", "key"))
    title = _first_text(payload, ("title", "name"))
    if issue_id is None or title is None:
        return None

    clean_title = title.strip()
    if clean_title == "" or _has_research_prefix(clean_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {clean_title}",
    }


def _flatten_event(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common Cursor and Linear webhook wrappers into one payload."""

    merged: dict[str, Any] = {}

    def merge_mapping(value: Any) -> None:
        if isinstance(value, Mapping):
            merged.update(value)

    merge_mapping(event.get("issue"))

    data = event.get("data")
    if isinstance(data, Mapping):
        merge_mapping(data.get("issue"))
        merge_mapping(data)

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        merge_mapping(trigger_context.get("issue"))
        merge_mapping(trigger_context)

    merge_mapping(event)
    return merged


def _is_status_change_event(payload: Mapping[str, Any]) -> bool:
    trigger_values = (
        payload.get("trigger"),
        payload.get("webhookType"),
        payload.get("action"),
        payload.get("type"),
    )

    if any(_normalize_token(value) in {"statuschanged", "statuschange"} for value in trigger_values):
        return True

    if any(_normalize_token(value) in {"issueupdated", "updatedissue", "update", "issue"} for value in trigger_values):
        return _updated_fields_include_status(payload)

    return False


def _updated_fields_include_status(payload: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        fields = payload.get(key)
        if _field_list_includes_status(fields):
            return True

    changes = payload.get("changes")
    if isinstance(changes, Mapping):
        return any(_normalize_field_name(field) in STATUS_FIELDS for field in changes)

    return False


def _field_list_includes_status(fields: Any) -> bool:
    if isinstance(fields, str):
        return _normalize_field_name(fields) in STATUS_FIELDS

    if isinstance(fields, Mapping):
        return any(_normalize_field_name(field) in STATUS_FIELDS for field in fields)

    if isinstance(fields, list | tuple | set):
        return any(_normalize_field_name(field) in STATUS_FIELDS for field in fields)

    return False


def _extract_new_status(payload: Mapping[str, Any]) -> str | None:
    for key in ("newStatus", "new_status", "statusName", "status_name"):
        value = _text_or_name(payload.get(key))
        if value is not None:
            return value

    changes = payload.get("changes")
    if isinstance(changes, Mapping):
        for key in ("status", "state", "workflowState", "workflow_state"):
            value = _status_from_change(changes.get(key))
            if value is not None:
                return value

    for key in ("status", "state", "workflowState", "workflow_state"):
        value = _text_or_name(payload.get(key))
        if value is not None:
            return value

    return None


def _status_from_change(change: Any) -> str | None:
    if isinstance(change, Mapping):
        for key in ("to", "newValue", "new_value", "after", "name"):
            value = _text_or_name(change.get(key))
            if value is not None:
                return value
    return _text_or_name(change)


def _text_or_name(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped if stripped else None

    if isinstance(value, Mapping):
        return _text_or_name(value.get("name"))

    return None


def _first_text(payload: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = _text_or_name(payload.get(key))
        if value is not None:
            return value
    return None


def _has_research_prefix(title: str) -> bool:
    return re.match(rf"^\s*{re.escape(PREFIX)}\b", title, re.IGNORECASE) is not None


def _normalize_status(value: str | None) -> str | None:
    if value is None:
        return None
    words = re.sub(r"([a-z])([A-Z])", r"\1 \2", value)
    words = re.sub(r"[^a-zA-Z0-9]+", " ", words)
    return " ".join(words.casefold().split())


def _normalize_token(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def _normalize_field_name(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
