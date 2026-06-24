"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"

_STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow_state"}


def build_issue_title_update(event: Any) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to To Research.

    The automation runner passes payloads from different sources over time:
    Cursor's flat ``triggerContext`` shape, Linear's nested ``data.issue`` shape,
    and generic issue update webhook shapes. This function accepts those variants
    but only emits an update when the event is a status/state change to
    ``to research`` and the issue title is not already prefixed.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    status = _extract_new_status(event)
    if _normalize_text(status) != _normalize_text(TARGET_STATUS):
        return None

    title = _extract_issue_title(event)
    issue_id = _extract_issue_id(event)
    if not title or not issue_id:
        return None

    title = title.strip()
    if not title or _has_prefix(title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    event_names = [_normalize_text(value) for value in _event_name_values(event)]

    if any("status changed" in name or "state changed" in name for name in event_names):
        return True

    is_generic_update = any(
        name in {"update", "updated", "issue update", "issue updated", "updated issue"}
        for name in event_names
    )
    return is_generic_update and _updated_status_fields(event)


def _event_name_values(event: Mapping[str, Any]) -> Iterable[Any]:
    keys = {"trigger", "webhookType", "webhook_type", "action", "type", "eventType", "event_type"}
    for payload in _iter_mappings(event):
        for key in keys:
            if key in payload:
                yield payload[key]


def _updated_status_fields(event: Mapping[str, Any]) -> bool:
    for payload in _iter_mappings(event):
        for key in ("updatedFields", "updated_fields"):
            if _contains_status_field(payload.get(key)):
                return True

        changes = payload.get("changes") or payload.get("changedFields") or payload.get("changed_fields")
        if isinstance(changes, Mapping):
            if any(_is_status_field_name(key) for key in changes):
                return True
        elif _contains_status_field(changes):
            return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field_name(value)
    if isinstance(value, Mapping):
        return any(_is_status_field_name(key) for key in value)
    if isinstance(value, Iterable):
        return any(_contains_status_field(item) for item in value)
    return False


def _is_status_field_name(value: Any) -> bool:
    normalized = _normalize_key(value)
    return normalized in _STATUS_FIELD_NAMES


def _extract_new_status(event: Mapping[str, Any]) -> str | None:
    explicit_keys = (
        "newStatus",
        "new_status",
        "statusName",
        "status_name",
        "newState",
        "new_state",
        "stateName",
        "state_name",
        "workflowStateName",
        "workflow_state_name",
    )
    for payload in _priority_mappings(event):
        value = _first_string(payload, explicit_keys)
        if value:
            return value

    for payload in _priority_mappings(event):
        value = payload.get("status")
        if isinstance(value, str) and value.strip():
            return value
        value = _name_from_mapping(value)
        if value:
            return value

        for key in ("state", "workflowState", "workflow_state"):
            value = _name_from_mapping(payload.get(key))
            if value:
                return value
            direct_value = payload.get(key)
            if isinstance(direct_value, str) and direct_value.strip():
                return direct_value

    return None


def _extract_issue_title(event: Mapping[str, Any]) -> str | None:
    for payload in _priority_mappings(event):
        title = _first_string(payload, ("title",))
        if title:
            return title
    return None


def _extract_issue_id(event: Mapping[str, Any]) -> str | None:
    keys = ("issueId", "issue_id", "identifier", "key", "id")
    for payload in _priority_mappings(event):
        issue_id = _first_string(payload, keys)
        if issue_id:
            return issue_id
    return None


def _priority_mappings(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return likely issue payloads before generic wrapper payloads."""

    result: list[Mapping[str, Any]] = []
    for path in (
        ("automation_trigger_info", "triggerContext"),
        ("automationTriggerInfo", "triggerContext"),
        ("triggerContext",),
        ("trigger_context",),
        ("data", "issue"),
        ("issue",),
        ("data",),
        (),
    ):
        payload = _get_path(event, path)
        if isinstance(payload, Mapping) and payload not in result:
            result.append(payload)
    return result


def _iter_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if not isinstance(value, Mapping):
        return

    yield value
    for nested_value in value.values():
        if isinstance(nested_value, Mapping):
            yield from _iter_mappings(nested_value)
        elif isinstance(nested_value, list):
            for item in nested_value:
                if isinstance(item, Mapping):
                    yield from _iter_mappings(item)


def _get_path(payload: Mapping[str, Any], path: tuple[str, ...]) -> Any:
    current: Any = payload
    for key in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current


def _first_string(payload: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _name_from_mapping(value: Any) -> str | None:
    if not isinstance(value, Mapping):
        return None
    return _first_string(value, ("name", "title"))


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def _normalize_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", _normalize_text(value))


def _normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    normalized = re.sub(r"[^a-zA-Z0-9]+", " ", spaced)
    return " ".join(normalized.lower().split())


def _main() -> int:
    payload = json.load(sys.stdin)
    update = build_issue_title_update(payload)
    if update is not None:
        json.dump(update, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
