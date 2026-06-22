"""Build Linear issue title updates for issues moved to research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_TRIGGER_KEYS = ("trigger", "webhookType", "webhook_type", "action", "type")
_STATUS_FIELD_NAMES = {
    "status",
    "status_id",
    "state",
    "state_id",
    "workflowstate",
    "workflowstate_id",
    "workflow_state",
    "workflow_state_id",
}
_DIRECT_STATUS_TRIGGERS = {
    "status changed",
    "status change",
    "status updated",
    "state changed",
    "workflow state changed",
}
_GENERIC_UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear issue-title update action when an issue moves to research.

    The function is intentionally side-effect free. Automation runners can call it
    with a Cursor trigger payload or a Linear webhook payload, then apply the
    returned action with the Linear API.
    """

    if not isinstance(event, Mapping):
        return None

    context = _trigger_context(event)
    if context is None:
        return None

    if not _is_status_change_event(context):
        return None

    status = _changed_status(context)
    if _normalize(status) != TARGET_STATUS:
        return None

    issue_id = _string_value(context, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _string_value(context, ("title", "name"))
    if not issue_id or not title:
        return None

    if _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _trigger_context(event: Mapping[str, Any]) -> dict[str, Any] | None:
    candidates = _candidate_mappings(event)
    if not candidates:
        return None

    merged: dict[str, Any] = {}
    for candidate in reversed(candidates):
        merged.update(candidate)

    return merged


def _candidate_mappings(event: Mapping[str, Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping):
            candidates.append(dict(value))

    add(event)

    trigger_info = event.get("automation_trigger_info") or event.get("automationTriggerInfo")
    if isinstance(trigger_info, Mapping):
        add(trigger_info)
        add(trigger_info.get("triggerContext"))
        add(trigger_info.get("trigger_context"))

    add(event.get("triggerContext"))
    add(event.get("trigger_context"))

    data = event.get("data")
    if isinstance(data, Mapping):
        add(data)
        add(data.get("issue"))
        add(data.get("node"))
        add(data.get("object"))

    add(event.get("issue"))

    return candidates


def _is_status_change_event(context: Mapping[str, Any]) -> bool:
    triggers = {
        _normalize(context[key])
        for key in _TRIGGER_KEYS
        if key in context and context.get(key) is not None
    }

    if triggers & _DIRECT_STATUS_TRIGGERS:
        return True

    if triggers & _GENERIC_UPDATE_TRIGGERS:
        return _updated_status_fields(context)

    return False


def _updated_status_fields(context: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        if _contains_status_field(context.get(key)):
            return True

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        for key in changes:
            if _is_status_field_name(key):
                return True
    elif _contains_status_field(changes):
        return True

    for key in ("updatedFrom", "updated_from"):
        if _contains_status_field(context.get(key)):
            return True

    return False


def _changed_status(context: Mapping[str, Any]) -> str | None:
    for key in ("newStatus", "new_status", "toStatus", "to_status"):
        status = _status_name(context.get(key))
        if status:
            return status

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        for key, value in changes.items():
            if _is_status_field_name(key):
                status = _status_name(value)
                if status:
                    return status
                if isinstance(value, Mapping):
                    for nested_key in ("to", "newValue", "new_value", "after"):
                        status = _status_name(value.get(nested_key))
                        if status:
                            return status

    for key in ("status", "state", "workflowState", "workflow_state"):
        status = _status_name(context.get(key))
        if status:
            return status

    return None


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field_name(value)

    if isinstance(value, Mapping):
        return any(_is_status_field_name(key) for key in value)

    if isinstance(value, (list, tuple, set)):
        return any(_contains_status_field(item) for item in value)

    return False


def _status_name(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "value"):
            status = _status_name(value.get(key))
            if status:
                return status

    return None


def _string_value(context: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = context.get(key)
        if isinstance(value, str):
            stripped = value.strip()
            if stripped:
                return stripped
    return None


def _has_prefix(title: str) -> bool:
    return title.strip().casefold().startswith(PREFIX.casefold())


def _normalize(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    words = re.sub(r"[^A-Za-z0-9]+", " ", spaced).strip().casefold()
    return re.sub(r"\s+", " ", words)


def _normalize_field_name(value: Any) -> str:
    return re.sub(r"[^a-z0-9_]", "", _normalize(value).replace(" ", "_"))


def _is_status_field_name(value: Any) -> bool:
    return _normalize_field_name(value) in _STATUS_FIELD_NAMES


def main() -> int:
    payload = json.load(sys.stdin)
    update = build_issue_title_update(payload)
    if update is None:
        return 0

    print(json.dumps(update, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
