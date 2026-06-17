"""Build Linear issue title updates for research status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflowstate",
    "workflowstatus",
}
_STATUS_TRIGGER_NAMES = {
    "statuschanged",
    "statuschange",
    "statechanged",
    "statechange",
    "workflowstatechanged",
    "workflowstatuschanged",
}
_ISSUE_UPDATE_TRIGGER_NAMES = {
    "update",
    "updated",
    "issueupdate",
    "issueupdated",
    "updatedissue",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to "to research".

    The automation trigger can arrive as a flat Cursor trigger context, wrapped in
    ``triggerContext``, or as a nested Linear webhook payload. For non-matching
    payloads, the function returns ``None`` so callers can safely no-op.
    """

    if not isinstance(event, Mapping):
        return None

    payload = _flatten_payload(event)
    if not _is_status_transition(payload):
        return None

    new_status = _new_status(payload)
    if _normalize(new_status) != _normalize(TARGET_STATUS):
        return None

    issue_id = _first_text(payload, ("issueId", "issue_id", "id", "identifier", "key"))
    title = _first_text(payload, ("title", "name"))
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


def _flatten_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common wrapper objects into one view of trigger and issue fields."""

    flattened: dict[str, Any] = {}

    def merge(value: Any) -> None:
        if isinstance(value, Mapping):
            flattened.update(value)

    issue = _mapping_at(event, ("data", "issue")) or _mapping_at(event, ("issue",))
    trigger_context = _mapping_at(event, ("triggerContext",))
    data = _mapping_at(event, ("data",))

    merge(issue)
    merge(data)
    merge(trigger_context)
    merge(event)

    if issue:
        for key in ("id", "issueId", "issue_id", "identifier", "key", "title", "name"):
            if key in issue and key not in flattened:
                flattened[key] = issue[key]

    for status_key in ("state", "status", "workflowState", "workflowStatus"):
        value = flattened.get(status_key)
        name = _name_from(value)
        if name and f"{status_key}Name" not in flattened:
            flattened[f"{status_key}Name"] = name

    return flattened


def _is_status_transition(payload: Mapping[str, Any]) -> bool:
    trigger_values = [
        payload.get("trigger"),
        payload.get("webhookType"),
        payload.get("action"),
        payload.get("type"),
    ]
    normalized_triggers = {_normalize(value) for value in trigger_values if value is not None}

    if normalized_triggers & _STATUS_TRIGGER_NAMES:
        return True

    if normalized_triggers & _ISSUE_UPDATE_TRIGGER_NAMES:
        return _changed_status_field(payload)

    return False


def _changed_status_field(payload: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "changedFields"):
        fields = payload.get(key)
        if isinstance(fields, str):
            field_values = [fields]
        elif isinstance(fields, (list, tuple, set)):
            field_values = fields
        else:
            field_values = []

        if any(_normalize(field) in _STATUS_FIELD_NAMES for field in field_values):
            return True

    changes = payload.get("changes")
    if isinstance(changes, Mapping):
        return any(_normalize(field) in _STATUS_FIELD_NAMES for field in changes)

    return False


def _new_status(payload: Mapping[str, Any]) -> str | None:
    for key in (
        "newStatus",
        "new_status",
        "toStatus",
        "to_status",
        "statusName",
        "stateName",
        "workflowStateName",
        "workflowStatusName",
        "status",
        "state",
        "workflowState",
        "workflowStatus",
    ):
        value = payload.get(key)
        text = _name_from(value)
        if text:
            return text

    changes = payload.get("changes")
    if isinstance(changes, Mapping):
        for key in ("status", "state", "workflowState", "workflowStatus"):
            value = changes.get(key)
            if isinstance(value, Mapping):
                text = _name_from(value.get("to") or value.get("new") or value.get("newValue"))
                if text:
                    return text

    return None


def _mapping_at(payload: Mapping[str, Any], path: tuple[str, ...]) -> Mapping[str, Any] | None:
    current: Any = payload
    for key in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current if isinstance(current, Mapping) else None


def _first_text(payload: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _name_from(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        name = value.get("name") or value.get("title")
        if isinstance(name, str):
            return name
    return None


def _normalize(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is None:
        return 0
    print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
