"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}


def build_issue_title_update(event: Any) -> dict[str, str] | None:
    """Return a Linear issue title update action for matching status changes."""

    if not isinstance(event, Mapping):
        return None

    payload = _merge_payload(event)
    if not _is_status_change_event(event, payload):
        return None

    status = _extract_new_status(event, payload)
    if _normalize_text(status) != _normalize_text(TARGET_STATUS):
        return None

    issue_id = _first_text(payload, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_text(payload, ("title", "name"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_title_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def handle_issue_status_changed(event: Any) -> dict[str, str] | None:
    """Compatibility wrapper for automation entry points."""

    return build_issue_title_update(event)


def _merge_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten common Cursor and Linear webhook wrappers into one payload."""

    payload: dict[str, Any] = {}

    for key in ("issue", "data", "triggerContext"):
        nested = event.get(key)
        if isinstance(nested, Mapping):
            payload.update(_merge_payload(nested))

    payload.update(event)

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        payload.update(issue)

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            payload.update(issue)
        payload.update(data)

    context = event.get("triggerContext")
    if isinstance(context, Mapping):
        payload.update(context)

    return payload


def _is_status_change_event(event: Mapping[str, Any], payload: Mapping[str, Any]) -> bool:
    trigger_values = [
        _first_text(payload, ("trigger", "webhookType", "action", "type")),
        _first_text(event, ("trigger", "webhookType", "action", "type")),
    ]

    normalized_triggers = {_normalize_text(value) for value in trigger_values if value}
    if any(value in {"statuschanged", "statuschange"} for value in normalized_triggers):
        return True
    if any(value in {"issueupdated", "updatedissue", "update"} for value in normalized_triggers):
        return _updated_status_fields(payload)

    return _updated_status_fields(payload)


def _updated_status_fields(payload: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        fields = payload.get(key)
        if isinstance(fields, str):
            fields = [fields]
        if isinstance(fields, Sequence) and not isinstance(fields, (str, bytes, bytearray)):
            for field in fields:
                if _normalize_field_name(field) in STATUS_FIELDS:
                    return True

    changes = payload.get("changes")
    if isinstance(changes, Mapping):
        return any(_normalize_field_name(field) in STATUS_FIELDS for field in changes)

    return False


def _extract_new_status(event: Mapping[str, Any], payload: Mapping[str, Any]) -> str | None:
    for source in (payload, event):
        for key in ("newStatus", "new_status"):
            status = _extract_status_value(source.get(key))
            if status:
                return status

    changes = payload.get("changes")
    if isinstance(changes, Mapping):
        for key in ("status", "state", "workflowState", "workflow_state"):
            status = _extract_change_status(changes.get(key))
            if status:
                return status

    for source in (payload, event):
        for key in ("status", "state", "workflowState", "workflow_state"):
            status = _extract_status_value(source.get(key))
            if status:
                return status

    return None


def _extract_change_status(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("to", "new", "newValue", "new_value", "name"):
            status = _extract_status_value(value.get(key))
            if status:
                return status
    return _extract_status_value(value)


def _extract_status_value(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    if isinstance(value, Mapping):
        for key in ("name", "status", "state", "workflowState", "workflow_state"):
            status = _extract_status_value(value.get(key))
            if status:
                return status
    return None


def _first_text(payload: Mapping[str, Any], keys: Sequence[str]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _has_title_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def _normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    with_spaces = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value.strip())
    return re.sub(r"[^a-z0-9]+", "", with_spaces.lower())


def _normalize_field_name(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^a-z0-9]+", "", value.strip().lower())


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
