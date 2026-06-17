"""Build Linear issue-title updates for research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}
DIRECT_STATUS_TRIGGERS = {"statuschanged", "statuschange", "statusupdated", "statusupdate"}
GENERIC_UPDATE_TRIGGERS = {
    "issueupdated",
    "updatedissue",
    "update",
    "updated",
    "issueupdate",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to To research."""

    if not isinstance(event, Mapping):
        return None

    payload = _merged_payload(event)
    if not _is_status_change(payload):
        return None

    status = _extract_new_status(payload)
    if _normalize_text(status) != _normalize_text(TARGET_STATUS):
        return None

    issue_id = _extract_text(payload, ("issueId", "issue_id", "id", "identifier", "key"))
    title = _extract_text(payload, ("title", "name"))
    if not issue_id or not title:
        return None

    if title.casefold().startswith(PREFIX.casefold()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _merged_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten common Cursor and Linear webhook wrappers without losing metadata."""

    payload: dict[str, Any] = {}

    def merge(value: Any) -> None:
        if not isinstance(value, Mapping):
            return

        for key in ("triggerContext", "data", "issue"):
            nested = value.get(key)
            if isinstance(nested, Mapping):
                merge(nested)

        payload.update(value)

    merge(event)
    return payload


def _is_status_change(payload: Mapping[str, Any]) -> bool:
    trigger_values = [
        payload.get("trigger"),
        payload.get("action"),
        payload.get("type"),
        payload.get("webhookType"),
        payload.get("triggerType"),
    ]
    normalized_triggers = {_normalize_identifier(value) for value in trigger_values if value}

    if normalized_triggers & DIRECT_STATUS_TRIGGERS:
        return True

    if normalized_triggers & GENERIC_UPDATE_TRIGGERS:
        return _updated_fields_include_status(payload)

    return False


def _updated_fields_include_status(payload: Mapping[str, Any]) -> bool:
    updated_fields = payload.get("updatedFields")
    if isinstance(updated_fields, str):
        updated_fields = [updated_fields]
    if isinstance(updated_fields, (list, tuple, set)):
        if any(_normalize_identifier(field) in STATUS_FIELDS for field in updated_fields):
            return True

    changes = payload.get("changes")
    if isinstance(changes, Mapping):
        return any(_normalize_identifier(field) in STATUS_FIELDS for field in changes)

    return False


def _extract_new_status(payload: Mapping[str, Any]) -> str | None:
    for key in ("newStatus", "new_status", "statusName", "stateName", "workflowStateName"):
        value = payload.get(key)
        text = _text_or_name(value)
        if text:
            return text

    changes = payload.get("changes")
    if isinstance(changes, Mapping):
        for key in ("status", "state", "workflowState", "workflow_state"):
            text = _changed_value_text(changes.get(key))
            if text:
                return text

    for key in ("status", "state", "workflowState", "workflow_state"):
        value = payload.get(key)
        text = _text_or_name(value)
        if text:
            return text

    return None


def _changed_value_text(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("newValue", "new", "to", "after", "name"):
            text = _text_or_name(value.get(key))
            if text:
                return text

    return _text_or_name(value)


def _extract_text(payload: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        text = _text_or_name(payload.get(key))
        if text:
            return text
    return None


def _text_or_name(value: Any) -> str | None:
    if isinstance(value, str):
        text = value.strip()
        return text or None
    if isinstance(value, Mapping):
        for key in ("name", "title", "id", "identifier", "key"):
            text = _text_or_name(value.get(key))
            if text:
                return text
    return None


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[_\-\s]+", " ", text)
    return text.casefold()


def _normalize_identifier(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", _normalize_text(value))


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        json.dump(action, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
