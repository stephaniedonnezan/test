"""Build Linear issue title updates for Cursor research automations."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
ACTION = "update_issue_title"

_STATUS_FIELDS = frozenset({"status", "state", "workflowstate", "workflow_status"})
_DIRECT_STATUS_TRIGGERS = frozenset(
    {
        "statuschanged",
        "statuschange",
        "statusupdated",
        "statusupdate",
        "statechanged",
        "statechange",
        "workflowstatechanged",
        "workflowstatechange",
    }
)
_GENERIC_UPDATE_TRIGGERS = frozenset(
    {
        "update",
        "updated",
        "issueupdate",
        "issueupdated",
        "updatedissue",
    }
)


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title-update action when a Linear issue moves to To Research."""

    if not isinstance(event, Mapping):
        return None

    payload = _flatten_payload(event)
    if not _is_status_change(payload):
        return None

    new_status = _new_status(payload)
    if _normalize_token(new_status) != "toresearch":
        return None

    issue_id = _first_text(payload, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_text(payload, ("title", "name"))
    if not issue_id or not title:
        return None

    return {"action": ACTION, "issueId": issue_id, "title": _prefixed_title(title)}


def _flatten_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common Cursor and Linear wrapper shapes into one lookup dictionary."""

    payload: dict[str, Any] = {}

    def visit(value: Any) -> None:
        if not isinstance(value, Mapping):
            return

        issue = value.get("issue")
        data = value.get("data")
        trigger_context = value.get("triggerContext")
        automation_info = value.get("automation_trigger_info")
        if isinstance(automation_info, Mapping):
            visit(automation_info)
        if isinstance(trigger_context, Mapping):
            visit(trigger_context)
        if isinstance(data, Mapping):
            visit(data)
        if isinstance(issue, Mapping):
            visit(issue)

        payload.update(value)

    visit(event)
    return payload


def _is_status_change(payload: Mapping[str, Any]) -> bool:
    trigger_values = [
        payload.get("trigger"),
        payload.get("webhookType"),
        payload.get("action"),
        payload.get("type"),
    ]
    normalized_triggers = {_normalize_token(value) for value in trigger_values if value}

    if normalized_triggers & _DIRECT_STATUS_TRIGGERS:
        return True

    if normalized_triggers & _GENERIC_UPDATE_TRIGGERS:
        return _updated_fields_include_status(payload)

    return False


def _updated_fields_include_status(payload: Mapping[str, Any]) -> bool:
    updated_fields = payload.get("updatedFields")
    if isinstance(updated_fields, str):
        updated_fields = [updated_fields]
    if isinstance(updated_fields, list):
        for field in updated_fields:
            if _normalize_field(field) in _STATUS_FIELDS:
                return True

    changes = payload.get("changes")
    if isinstance(changes, Mapping):
        for field in changes:
            if _normalize_field(field) in _STATUS_FIELDS:
                return True
    elif isinstance(changes, list):
        for change in changes:
            if isinstance(change, str) and _normalize_field(change) in _STATUS_FIELDS:
                return True
            if isinstance(change, Mapping):
                field = change.get("field") or change.get("fieldName") or change.get("name")
                if _normalize_field(field) in _STATUS_FIELDS:
                    return True

    return False


def _new_status(payload: Mapping[str, Any]) -> Any:
    for key in ("newStatus", "new_status", "statusName", "stateName", "workflowStateName"):
        value = payload.get(key)
        if value:
            return value

    changes = payload.get("changes")
    if isinstance(changes, Mapping):
        for field, change in changes.items():
            if _normalize_field(field) not in _STATUS_FIELDS:
                continue
            if isinstance(change, Mapping):
                return (
                    change.get("newValue")
                    or change.get("to")
                    or change.get("after")
                    or change.get("name")
                )
            return change
    elif isinstance(changes, list):
        for change in changes:
            if not isinstance(change, Mapping):
                continue
            field = change.get("field") or change.get("fieldName") or change.get("name")
            if _normalize_field(field) not in _STATUS_FIELDS:
                continue
            return change.get("newValue") or change.get("to") or change.get("after")

    for key in ("status", "state", "workflowState"):
        value = payload.get(key)
        if isinstance(value, Mapping):
            name = value.get("name")
            if name:
                return name
        elif value:
            return value

    return None


def _first_text(payload: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _prefixed_title(title: str) -> str:
    stripped = title.strip()
    if stripped.lower().startswith(PREFIX.lower()):
        return stripped
    return f"{PREFIX}: {stripped}"


def _normalize_field(value: Any) -> str:
    return _normalize_token(value).replace("workflowstatus", "workflow_status")


def _normalize_token(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is None:
        return 0
    json.dump(update, sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
