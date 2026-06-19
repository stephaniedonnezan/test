"""Build Linear issue title updates for issues entering research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_TRIGGER_KEYS = ("trigger", "webhookType", "action", "type", "event", "eventType")
_EXPLICIT_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "newWorkflowState",
    "new_workflow_state",
    "toStatus",
    "to_status",
    "toState",
    "to_state",
    "toWorkflowState",
    "to_workflow_state",
    "statusName",
    "status_name",
    "stateName",
    "state_name",
    "workflowStateName",
    "workflow_state_name",
)
_CURRENT_STATUS_KEYS = ("status", "state", "workflowState", "workflow_state")
_ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "key", "id")
_TITLE_KEYS = ("title",)
_UPDATED_FIELDS_KEYS = (
    "updatedFields",
    "updated_fields",
    "changedFields",
    "changed_fields",
)
_CHANGES_KEYS = ("changes", "changed", "change")
_CHANGE_TO_KEYS = (
    "to",
    "after",
    "new",
    "newValue",
    "new_value",
    "current",
    "value",
)
_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflowstate",
    "workflowstateid",
    "stateid",
    "statusid",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to research.

    The function is intentionally side-effect free so the automation runtime can
    decide how to apply the returned action.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    new_status = _extract_new_status(event)
    if not _is_target_status(new_status):
        return None

    issue_id = _extract_issue_value(event, _ISSUE_ID_KEYS)
    title = _extract_issue_value(event, _TITLE_KEYS)
    if not issue_id or not title or _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    trigger_values = [_normalize_text(value) for value in _trigger_values(event)]

    if any(_is_direct_status_trigger(value) for value in trigger_values):
        return True

    if any(_is_generic_update_trigger(value) for value in trigger_values):
        return _has_status_change_metadata(event)

    return False


def _is_direct_status_trigger(value: str) -> bool:
    if not value:
        return False

    return (
        value in {"status changed", "state changed", "workflow state changed"}
        or "status changed" in value
        or "state changed" in value
        or "workflow state changed" in value
    )


def _is_generic_update_trigger(value: str) -> bool:
    return value in {"update", "updated", "issue update", "issue updated", "updated issue"}


def _has_status_change_metadata(event: Mapping[str, Any]) -> bool:
    return (
        _updated_fields_include_status(event)
        or _changes_include_status(event)
        or _has_any_key(event, _EXPLICIT_STATUS_KEYS)
    )


def _extract_new_status(event: Mapping[str, Any]) -> Any:
    explicit = _extract_from_keys(_event_containers(event), _EXPLICIT_STATUS_KEYS)
    if explicit is not None:
        return explicit

    changed = _extract_changed_status(event)
    if changed is not None:
        return changed

    return _extract_from_keys(_event_containers(event), _CURRENT_STATUS_KEYS)


def _extract_changed_status(event: Mapping[str, Any]) -> Any:
    for changes in _values_for_keys(event, _CHANGES_KEYS):
        status = _status_from_changes(changes)
        if status is not None:
            return status
    return None


def _status_from_changes(changes: Any) -> Any:
    if isinstance(changes, Mapping):
        if any(_is_status_field(key) for key in changes):
            for key, value in changes.items():
                if _is_status_field(key):
                    return _extract_change_destination(value)

        for value in changes.values():
            status = _status_from_changes(value)
            if status is not None:
                return status

    if _is_sequence(changes):
        for item in changes:
            status = _status_from_changes(item)
            if status is not None:
                return status

    return None


def _extract_change_destination(change: Any) -> Any:
    if isinstance(change, Mapping):
        for key in _CHANGE_TO_KEYS:
            if key in change:
                return _status_name(change[key])
        return _status_name(change)
    return _status_name(change)


def _updated_fields_include_status(event: Mapping[str, Any]) -> bool:
    for fields in _values_for_keys(event, _UPDATED_FIELDS_KEYS):
        if isinstance(fields, Mapping):
            candidates: Iterable[Any] = fields.keys()
        elif _is_sequence(fields):
            candidates = fields
        else:
            candidates = (fields,)

        if any(_is_status_field(field) for field in candidates):
            return True

    return False


def _changes_include_status(event: Mapping[str, Any]) -> bool:
    for changes in _values_for_keys(event, _CHANGES_KEYS):
        if _status_from_changes(changes) is not None:
            return True
    return False


def _trigger_values(event: Mapping[str, Any]) -> list[Any]:
    values: list[Any] = []
    for container in _event_containers(event):
        for key in _TRIGGER_KEYS:
            if key in container:
                values.append(container[key])
    return values


def _event_containers(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return useful payload layers from outer metadata to nested issue data."""

    containers: list[Mapping[str, Any]] = []

    automation_info = event.get("automation_trigger_info")
    if isinstance(automation_info, Mapping):
        trigger_context = automation_info.get("triggerContext")
        if isinstance(trigger_context, Mapping):
            containers.append(trigger_context)

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        containers.append(trigger_context)

    containers.append(event)

    for key in ("data", "issue", "payload"):
        value = event.get(key)
        if isinstance(value, Mapping):
            containers.append(value)
            nested_issue = value.get("issue")
            if isinstance(nested_issue, Mapping):
                containers.append(nested_issue)
            nested_payload = value.get("payload")
            if isinstance(nested_payload, Mapping):
                containers.append(nested_payload)

    return containers


def _issue_containers(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    containers = _event_containers(event)
    issue_like: list[Mapping[str, Any]] = []
    metadata: list[Mapping[str, Any]] = []

    for container in containers:
        if "title" in container or "identifier" in container or "issueId" in container:
            issue_like.append(container)
        else:
            metadata.append(container)

    return issue_like + metadata


def _extract_issue_value(event: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for container in _issue_containers(event):
        for key in keys:
            value = _string_value(container.get(key))
            if value:
                return value
    return None


def _extract_from_keys(containers: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> Any:
    for container in containers:
        for key in keys:
            if key in container:
                value = _status_name(container[key])
                if value is not None:
                    return value
    return None


def _values_for_keys(value: Any, keys: Iterable[str]) -> Iterable[Any]:
    key_set = set(keys)
    if isinstance(value, Mapping):
        for key, child in value.items():
            if key in key_set:
                yield child
            yield from _values_for_keys(child, key_set)
    elif _is_sequence(value):
        for child in value:
            yield from _values_for_keys(child, key_set)


def _has_any_key(value: Any, keys: Iterable[str]) -> bool:
    key_set = set(keys)
    if isinstance(value, Mapping):
        return any(key in key_set or _has_any_key(child, key_set) for key, child in value.items())
    if _is_sequence(value):
        return any(_has_any_key(child, key_set) for child in value)
    return False


def _status_name(value: Any) -> Any:
    if isinstance(value, Mapping):
        for key in ("name", "title", "label", "value"):
            if key in value:
                return _status_name(value[key])
        return None
    return value


def _is_target_status(value: Any) -> bool:
    status = _string_value(_status_name(value))
    return _normalize_text(status) == TARGET_STATUS if status else False


def _is_status_field(value: Any) -> bool:
    text = _string_value(value)
    if not text:
        return False

    compact = re.sub(r"[^a-z0-9]+", "", _split_camel(text).casefold())
    return compact in _STATUS_FIELD_NAMES


def _has_research_prefix(title: str) -> bool:
    return re.match(r"^\s*cursor\s+researching\b", title, re.IGNORECASE) is not None


def _normalize_text(value: Any) -> str:
    text = _string_value(value)
    if not text:
        return ""

    text = _split_camel(text)
    text = re.sub(r"[^a-zA-Z0-9]+", " ", text)
    return " ".join(text.casefold().split())


def _split_camel(value: str) -> str:
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    return re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", value)


def _string_value(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _is_sequence(value: Any) -> bool:
    return isinstance(value, Iterable) and not isinstance(value, (str, bytes, Mapping))


def _main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as error:
        print(f"Invalid JSON: {error}", file=sys.stderr)
        return 1

    update = build_issue_title_update(event)
    print(json.dumps(update, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
