"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"

_STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow state"}
_DIRECT_STATUS_CHANGED_EVENTS = {
    "status changed",
    "status change",
    "status updated",
    "status update",
}
_GENERIC_UPDATE_EVENTS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to To Research.

    The function accepts both the flat Cursor automation trigger payload and
    nested Linear webhook-style payloads. It returns ``None`` for events that
    are not status changes to the target status, missing required issue data,
    or titles that are already prefixed.
    """

    if not isinstance(event, Mapping):
        return None

    mappings = list(_candidate_mappings(event))
    if not _is_status_change_event(mappings):
        return None

    new_status = _extract_new_status(mappings)
    if _normalize_text(new_status) != TARGET_STATUS:
        return None

    issue_id = _extract_first_text(mappings, ("id", "issueId", "issue_id", "identifier", "key"))
    title = _extract_first_text(mappings, ("title", "issueTitle", "issue_title", "name"))
    if not issue_id or not title:
        return None

    clean_title = title.strip()
    if clean_title.lower().startswith(TITLE_PREFIX.lower()):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {clean_title}",
    }


def _candidate_mappings(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely metadata and issue objects, prioritizing trigger metadata."""

    for key in ("triggerContext", "trigger_context"):
        value = event.get(key)
        if isinstance(value, Mapping):
            yield value

    data = event.get("data")
    if isinstance(data, Mapping):
        yield data
        for key in ("issue", "node"):
            value = data.get(key)
            if isinstance(value, Mapping):
                yield value

    for key in ("issue", "node"):
        value = event.get(key)
        if isinstance(value, Mapping):
            yield value

    yield event


def _is_status_change_event(mappings: list[Mapping[str, Any]]) -> bool:
    event_names = []
    for mapping in mappings:
        for key in ("trigger", "action", "type", "webhookType", "webhook_type", "eventType"):
            value = mapping.get(key)
            if isinstance(value, str):
                event_names.append(_normalize_event_name(value))

    if any(name in _DIRECT_STATUS_CHANGED_EVENTS for name in event_names):
        return True

    if any(name in _GENERIC_UPDATE_EVENTS for name in event_names):
        return _payload_marks_status_as_changed(mappings)

    return False


def _payload_marks_status_as_changed(mappings: list[Mapping[str, Any]]) -> bool:
    for mapping in mappings:
        updated_fields = mapping.get("updatedFields") or mapping.get("updated_fields")
        if isinstance(updated_fields, Iterable) and not isinstance(updated_fields, (str, bytes, Mapping)):
            for field in updated_fields:
                field_name = _field_name(field)
                if field_name and _is_status_field(field_name):
                    return True

        changes = mapping.get("changes") or mapping.get("changedFields") or mapping.get("changed_fields")
        if isinstance(changes, Mapping):
            for field_name in changes:
                if _is_status_field(str(field_name)):
                    return True
        elif isinstance(changes, Iterable) and not isinstance(changes, (str, bytes)):
            for change in changes:
                field_name = _field_name(change)
                if field_name and _is_status_field(field_name):
                    return True

    return False


def _extract_new_status(mappings: list[Mapping[str, Any]]) -> str | None:
    explicit_status_keys = (
        "newStatus",
        "new_status",
        "toStatus",
        "to_status",
        "newState",
        "new_state",
        "toState",
        "to_state",
        "newWorkflowState",
        "new_workflow_state",
    )
    for mapping in mappings:
        value = _extract_first_status_value(mapping, explicit_status_keys)
        if value:
            return value

    for mapping in mappings:
        value = _extract_status_from_changes(mapping)
        if value:
            return value

    fallback_status_keys = ("status", "state", "workflowState", "workflow_state")
    for mapping in mappings:
        value = _extract_first_status_value(mapping, fallback_status_keys)
        if value:
            return value

    return None


def _extract_status_from_changes(mapping: Mapping[str, Any]) -> str | None:
    for container_key in ("changes", "changedFields", "changed_fields"):
        container = mapping.get(container_key)
        if isinstance(container, Mapping):
            for field_name, change in container.items():
                if _is_status_field(str(field_name)):
                    value = _new_value_from_change(change)
                    if value:
                        return value
        elif isinstance(container, Iterable) and not isinstance(container, (str, bytes, Mapping)):
            for change in container:
                field_name = _field_name(change)
                if field_name and _is_status_field(field_name):
                    value = _new_value_from_change(change)
                    if value:
                        return value

    for container_key in ("updatedFields", "updated_fields"):
        container = mapping.get(container_key)
        if isinstance(container, Iterable) and not isinstance(container, (str, bytes, Mapping)):
            for change in container:
                if isinstance(change, Mapping):
                    field_name = _field_name(change)
                    if field_name and _is_status_field(field_name):
                        value = _new_value_from_change(change)
                        if value:
                            return value
    return None


def _extract_first_status_value(mapping: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = mapping.get(key)
        extracted = _value_name(value)
        if extracted:
            return extracted
    return None


def _extract_first_text(mappings: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for mapping in mappings:
        for key in keys:
            value = mapping.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _new_value_from_change(change: Any) -> str | None:
    if isinstance(change, Mapping):
        for key in ("to", "after", "new", "newValue", "new_value", "value"):
            value = _value_name(change.get(key))
            if value:
                return value
    elif isinstance(change, (list, tuple)) and change:
        return _value_name(change[-1])
    return _value_name(change)


def _value_name(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value
    if isinstance(value, Mapping):
        for key in ("name", "title", "label", "value"):
            nested_value = value.get(key)
            if isinstance(nested_value, str) and nested_value.strip():
                return nested_value
    return None


def _field_name(field: Any) -> str | None:
    if isinstance(field, str):
        return field
    if isinstance(field, Mapping):
        for key in ("field", "fieldName", "field_name", "name", "key"):
            value = field.get(key)
            if isinstance(value, str):
                return value
    return None


def _is_status_field(field_name: str) -> bool:
    return _normalize_event_name(field_name) in _STATUS_FIELD_NAMES


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    return _normalize_event_name(value)


def _normalize_event_name(value: str) -> str:
    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    normalized = re.sub(r"[^a-zA-Z0-9]+", " ", separated).strip().lower()
    return re.sub(r"\s+", " ", normalized)


def main() -> int:
    """Read a JSON event from stdin and print the title update action."""

    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(build_issue_title_update(payload)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
