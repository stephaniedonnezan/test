"""Build Linear issue title update actions for research-status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {"status", "state", "workflowstate"}
_DIRECT_STATUS_CHANGE_SIGNALS = {
    "status change",
    "status changed",
    "state change",
    "state changed",
    "workflow state change",
    "workflow state changed",
}
_GENERIC_UPDATE_SIGNALS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title-update action when a Linear issue enters To Research.

    Cursor/Linear webhook payloads are not perfectly uniform, so this accepts
    flat trigger contexts, Cloud automation wrappers, and common nested Linear
    webhook shapes.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    if not _is_target_status(_extract_target_status(event)):
        return None

    issue_id = _extract_text(event, ("identifier", "key", "issueId", "issue_id", "issueIdentifier", "id"))
    title = _extract_text(event, ("title",))
    if issue_id is None or title is None:
        return None

    if title.lstrip().lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    signals = {_normalize_text(value) for value in _signal_values(event)}
    signals.discard("")

    if signals & _DIRECT_STATUS_CHANGE_SIGNALS:
        return True

    if signals & _GENERIC_UPDATE_SIGNALS:
        return _has_status_change_marker(event)

    return _has_status_change_marker(event) and not signals


def _signal_values(event: Mapping[str, Any]) -> Iterable[Any]:
    for mapping in _candidate_mappings(event):
        for key in ("trigger", "webhookType", "webhook_type", "action", "type", "event", "eventType"):
            if key in mapping:
                yield mapping[key]


def _has_status_change_marker(event: Mapping[str, Any]) -> bool:
    for mapping in _candidate_mappings(event):
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            if _field_collection_mentions_status(mapping.get(key)):
                return True

        changes = mapping.get("changes")
        if isinstance(changes, Mapping) and any(_is_status_field(key) for key in changes):
            return True

        updated_from = mapping.get("updatedFrom")
        if isinstance(updated_from, Mapping) and any(_is_status_field(key) for key in updated_from):
            return True

    return False


def _field_collection_mentions_status(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)

    if isinstance(value, Mapping):
        return any(_is_status_field(key) for key in value)

    if isinstance(value, Iterable):
        return any(_is_status_field(item) for item in value)

    return False


def _is_status_field(value: Any) -> bool:
    return _normalize_field_name(value) in _STATUS_FIELD_NAMES


def _extract_target_status(event: Mapping[str, Any]) -> str | None:
    mappings = list(_candidate_mappings(event))

    for key in ("newStatus", "new_status", "toStatus", "to_status"):
        for mapping in mappings:
            value = _status_value(mapping.get(key))
            if value:
                return value

    for mapping in mappings:
        changes_status = _status_from_changes(mapping.get("changes"))
        if changes_status:
            return changes_status

    for key in ("status", "state", "workflowState", "workflow_state"):
        for mapping in mappings:
            value = _status_value(mapping.get(key))
            if value:
                return value

    return None


def _status_from_changes(changes: Any) -> str | None:
    if not isinstance(changes, Mapping):
        return None

    for field_name in ("status", "state", "workflowState", "workflow_state"):
        if field_name not in changes:
            continue

        value = changes[field_name]
        if isinstance(value, Mapping):
            for key in ("to", "new", "newValue", "new_value", "after", "name"):
                status = _status_value(value.get(key))
                if status:
                    return status
        else:
            status = _status_value(value)
            if status:
                return status

    return None


def _status_value(value: Any) -> str | None:
    if isinstance(value, str):
        return _trim(value)

    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            status = _status_value(value.get(key))
            if status:
                return status

    return None


def _is_target_status(status: str | None) -> bool:
    return _normalize_text(status) == TARGET_STATUS


def _extract_text(event: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    mappings = list(_candidate_mappings(event))
    for key in keys:
        for mapping in mappings:
            value = mapping.get(key)
            if isinstance(value, str):
                text = _trim(value)
                if text:
                    return text
    return None


def _candidate_mappings(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    for path in (
        ("automation_trigger_info", "triggerContext"),
        ("triggerContext",),
        ("payload", "triggerContext"),
        ("data", "issue"),
        ("issue",),
        ("payload", "data", "issue"),
        ("data",),
        ("payload", "data"),
        ("payload", "issue"),
        (),
        ("payload",),
    ):
        mapping = _mapping_at_path(event, path)
        if mapping is not None:
            yield mapping


def _mapping_at_path(event: Mapping[str, Any], path: tuple[str, ...]) -> Mapping[str, Any] | None:
    current: Any = event
    for key in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current if isinstance(current, Mapping) else None


def _normalize_field_name(value: Any) -> str:
    return _normalize_text(value).replace(" ", "")


def _normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    value = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    value = re.sub(r"[^A-Za-z0-9]+", " ", value)
    return " ".join(value.lower().split())


def _trim(value: str) -> str | None:
    text = value.strip()
    return text or None


def main() -> int:
    """Read a JSON event from stdin and print the resulting action, if any."""

    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
