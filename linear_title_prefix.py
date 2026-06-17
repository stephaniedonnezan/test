"""Build Linear issue title updates for Cursor research status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {
    "status",
    "statusid",
    "state",
    "stateid",
    "workflowstate",
    "workflowstateid",
    "workflow_state",
    "workflow_state_id",
}
STATUS_CHANGE_TRIGGERS = {
    "status change",
    "status changed",
    "statuschange",
    "status changed issue",
    "issue status changed",
    "state change",
    "state changed",
    "issue state changed",
    "workflow state change",
    "workflow state changed",
}
GENERIC_UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to To Research.

    Cursor automation payloads usually provide a flat ``triggerContext`` object,
    while native Linear webhooks may nest issue data under ``data``/``issue``.
    The returned action is intentionally small so the caller can perform the
    Linear mutation outside this pure decision function.
    """

    if not isinstance(event, Mapping):
        return None

    payload = _payload(event)
    if not _is_status_change(payload):
        return None

    new_status = _new_status(payload)
    if _normalize(new_status) != TARGET_STATUS:
        return None

    issue_id = _string_value(payload, "issueId", "issue_id", "id", "identifier", "key")
    title = _string_value(payload, "title", "name")
    if not issue_id or not title:
        return None

    clean_title = title.strip()
    if _has_prefix(clean_title):
        prefixed_title = clean_title
    else:
        prefixed_title = f"{TITLE_PREFIX}: {clean_title}"

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": prefixed_title,
    }


def _payload(event: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten common Cursor and Linear webhook containers into one mapping."""

    flattened: dict[str, Any] = {}

    for container_key in ("issue", "data", "triggerContext"):
        container = event.get(container_key)
        if isinstance(container, Mapping):
            flattened.update(_payload(container))

    # Outer webhook metadata, such as action/type and explicit status values,
    # should take precedence over nested issue fields.
    flattened.update(event)
    return flattened


def _is_status_change(payload: Mapping[str, Any]) -> bool:
    trigger_names = [
        _normalize(payload.get(key))
        for key in ("trigger", "webhookType", "action", "type")
        if payload.get(key) is not None
    ]

    if any(name in STATUS_CHANGE_TRIGGERS for name in trigger_names):
        return True

    if not any(name in GENERIC_UPDATE_TRIGGERS for name in trigger_names):
        return False

    return _changed_status_field(payload)


def _changed_status_field(payload: Mapping[str, Any]) -> bool:
    updated_fields = payload.get("updatedFields")
    if _field_list_mentions_status(updated_fields):
        return True

    for key in ("changes", "updatedFrom", "previousValues"):
        changes = payload.get(key)
        if isinstance(changes, Mapping):
            if any(_field_name_mentions_status(field) for field in changes):
                return True

    return False


def _field_list_mentions_status(value: Any) -> bool:
    if isinstance(value, str):
        return _field_name_mentions_status(value)
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes, Mapping)):
        return any(_field_name_mentions_status(field) for field in value)
    return False


def _field_name_mentions_status(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    return _field_key(value) in STATUS_FIELDS


def _new_status(payload: Mapping[str, Any]) -> str | None:
    for key in ("newStatus", "new_status", "statusName", "stateName", "workflowStateName"):
        value = _string_value(payload, key)
        if value:
            return value

    for key in ("changes", "updatedFrom"):
        changes = payload.get(key)
        if isinstance(changes, Mapping):
            value = _changed_value(changes)
            if value:
                return value

    for key in ("status", "state", "workflowState", "workflow_state"):
        value = payload.get(key)
        if isinstance(value, Mapping):
            value = _string_value(value, "name")
        if isinstance(value, str) and value.strip():
            return value.strip()

    return None


def _changed_value(changes: Mapping[str, Any]) -> str | None:
    for field, change in changes.items():
        if not _field_name_mentions_status(field):
            continue

        if isinstance(change, Mapping):
            for key in ("to", "new", "newValue", "after", "value", "name"):
                value = change.get(key)
                if isinstance(value, Mapping):
                    value = _string_value(value, "name")
                if isinstance(value, str) and value.strip():
                    return value.strip()
        elif isinstance(change, str) and change.strip():
            return change.strip()

    return None


def _string_value(payload: Mapping[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _has_prefix(title: str) -> bool:
    return title.strip().lower().startswith(TITLE_PREFIX.lower())


def _normalize(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    with_spaces = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    with_spaces = re.sub(r"[_\-/]+", " ", with_spaces)
    return re.sub(r"\s+", " ", with_spaces).strip().lower()


def _field_key(value: str) -> str:
    return re.sub(r"[^a-z]", "", _normalize(value))


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    action = build_issue_title_update(event)
    if action is None:
        return 0

    print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
