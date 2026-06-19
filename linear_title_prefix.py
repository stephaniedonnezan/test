"""Build Linear issue title update actions for research status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "stateid",
    "workflowstate",
    "workflowstateid",
    "workflow_state",
    "workflow_state_id",
}
_DIRECT_STATUS_CHANGE_EVENTS = {
    "status changed",
    "status change",
    "status updated",
    "status update",
    "state changed",
    "state updated",
    "workflow state changed",
    "workflow state updated",
}
_ISSUE_UPDATE_EVENTS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to research.

    The Cursor automation payload is flat under ``triggerContext``. Linear
    webhooks are often nested under ``data`` or ``issue``. This function accepts
    those common shapes and leaves the actual side-effect to the caller.
    """

    if not isinstance(event, Mapping):
        return None

    payload = _merge_payload(event)
    if not _is_status_change_event(payload):
        return None

    status = _extract_new_status(payload)
    if _normalize_value(status) != TARGET_STATUS:
        return None

    issue_id = _first_text(payload, ("issueId", "issue_id", "id", "identifier", "key"))
    title = _first_text(payload, ("title", "name"))
    if not issue_id or not title:
        return None

    stripped_title = title.strip()
    if _has_research_prefix(stripped_title):
        new_title = stripped_title
    else:
        new_title = f"{PREFIX}: {stripped_title}"

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": new_title,
    }


def _merge_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for path in (
        ("issue",),
        ("data",),
        ("data", "issue"),
        ("triggerContext",),
    ):
        nested = _get_mapping(event, path)
        if nested:
            payload.update(nested)

    payload.update(event)
    return payload


def _is_status_change_event(payload: Mapping[str, Any]) -> bool:
    event_values = [
        _normalize_value(value)
        for key in ("trigger", "webhookType", "action", "type")
        if (value := payload.get(key)) is not None
    ]

    if any(value in _DIRECT_STATUS_CHANGE_EVENTS for value in event_values):
        return True

    if not any(value in _ISSUE_UPDATE_EVENTS for value in event_values):
        return False

    updated_fields = _collect_updated_field_names(payload)
    return any(field in _STATUS_FIELD_NAMES for field in updated_fields)


def _extract_new_status(payload: Mapping[str, Any]) -> Any:
    for key in (
        "newStatus",
        "new_status",
        "toStatus",
        "to_status",
        "status",
        "state",
        "workflowState",
        "workflow_state",
    ):
        value = payload.get(key)
        if value is not None:
            return _status_name(value)

    changes = payload.get("changes")
    if isinstance(changes, Mapping):
        for key in ("status", "state", "workflowState", "workflow_state"):
            value = changes.get(key)
            if value is None:
                continue
            if isinstance(value, Mapping):
                for changed_key in ("newValue", "new_value", "to", "after", "name"):
                    changed_value = value.get(changed_key)
                    if changed_value is not None:
                        return _status_name(changed_value)
            return _status_name(value)

    return None


def _status_name(value: Any) -> Any:
    if isinstance(value, Mapping):
        for key in ("name", "title", "label", "value"):
            nested = value.get(key)
            if nested is not None:
                return _status_name(nested)
    return value


def _collect_updated_field_names(payload: Mapping[str, Any]) -> set[str]:
    names: set[str] = set()
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        names.update(_normalized_field_names(payload.get(key)))

    changes = payload.get("changes")
    if isinstance(changes, Mapping):
        names.update(_normalize_field_name(key) for key in changes.keys())

    updated_from = payload.get("updatedFrom")
    if isinstance(updated_from, Mapping):
        names.update(_normalize_field_name(key) for key in updated_from.keys())

    return names


def _normalized_field_names(value: Any) -> set[str]:
    if value is None:
        return set()

    if isinstance(value, str):
        return {_normalize_field_name(value)}

    if isinstance(value, Mapping):
        return {_normalize_field_name(key) for key in value.keys()}

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return {
            _normalize_field_name(item)
            for item in value
            if isinstance(item, str)
        }

    return set()


def _normalize_field_name(value: str) -> str:
    return re.sub(r"[^a-z0-9_]", "", _split_camel_case(value).replace("-", "_").lower())


def _normalize_value(value: Any) -> str | None:
    value = _status_name(value)
    if not isinstance(value, str):
        return None

    split = _split_camel_case(value)
    normalized = re.sub(r"[^a-z0-9]+", " ", split.lower()).strip()
    return re.sub(r"\s+", " ", normalized)


def _split_camel_case(value: str) -> str:
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    return re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", value)


def _get_mapping(payload: Mapping[str, Any], path: tuple[str, ...]) -> Mapping[str, Any] | None:
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


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        json.dump(action, sys.stdout)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
