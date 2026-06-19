"""Build title-update actions for Linear issues entering research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {"state", "state id", "status", "status id", "workflow state"}
_DIRECT_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "newWorkflowState",
    "new_workflow_state",
    "statusName",
    "stateName",
    "workflowStateName",
)
_FALLBACK_STATUS_KEYS = ("status",)


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title-update action when a Linear issue moves to To Research."""

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    new_status = _extract_new_status(event)
    if _normalize_label(new_status) != TARGET_STATUS:
        return None

    issue_id = _extract_issue_id(event)
    title = _extract_title(event)
    if not issue_id or not title:
        return None

    stripped_title = title.strip()
    if not stripped_title or _already_prefixed(stripped_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {stripped_title}",
    }


def _extract_new_status(event: Mapping[str, Any]) -> str | None:
    for container in _priority_containers(event):
        value = _first_string_field(container, _DIRECT_STATUS_KEYS)
        if value:
            return value

    change_status = _extract_status_from_changes(event)
    if change_status:
        return change_status

    for container in _priority_containers(event):
        value = _first_string_field(container, _FALLBACK_STATUS_KEYS)
        if value:
            return value

        for nested_key in ("state", "workflowState", "workflow_state"):
            nested = container.get(nested_key)
            if isinstance(nested, Mapping):
                value = _first_string_field(nested, ("name", "title"))
                if value:
                    return value

    return None


def _extract_issue_id(event: Mapping[str, Any]) -> str | None:
    for container in _priority_containers(event):
        value = _first_string_field(container, ("issueId", "issue_id", "identifier", "key", "id"))
        if value:
            return value

    return None


def _extract_title(event: Mapping[str, Any]) -> str | None:
    for container in _priority_containers(event):
        value = _first_string_field(container, ("title",))
        if value:
            return value

    return None


def _priority_containers(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    containers: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in containers:
            containers.append(value)

    automation_info = event.get("automation_trigger_info")
    if isinstance(automation_info, Mapping):
        add(automation_info.get("triggerContext"))
        add(automation_info.get("trigger_context"))
        add(automation_info)

    trigger_context = event.get("triggerContext")
    trigger_context_snake = event.get("trigger_context")
    payload = event.get("payload")
    data = event.get("data")
    issue = event.get("issue")

    add(trigger_context)
    add(trigger_context_snake)
    add(issue)
    if isinstance(payload, Mapping):
        add(payload.get("triggerContext"))
        add(payload.get("trigger_context"))
        add(payload.get("issue"))
        payload_data = payload.get("data")
        if isinstance(payload_data, Mapping):
            add(payload_data.get("issue"))
        add(payload_data)
        add(payload)
    if isinstance(data, Mapping):
        add(data.get("issue"))
    add(data)
    add(event)

    return containers


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    for container in _walk_mappings(event):
        for key in ("trigger", "webhookType", "webhook_type", "eventType", "event_type"):
            if _is_status_changed_label(container.get(key)):
                return True

        for key in ("action", "type"):
            value = container.get(key)
            if _is_status_changed_label(value):
                return True
            if _is_issue_update_label(value) and _updated_fields_include_status(event):
                return True

    return False


def _updated_fields_include_status(event: Mapping[str, Any]) -> bool:
    field_keys = ("updatedFields", "updated_fields", "changedFields", "changed_fields")
    for container in _walk_mappings(event):
        for key in field_keys:
            for item in _iter_string_values(container.get(key)):
                normalized = _normalize_label(item)
                if any(field_name in normalized for field_name in _STATUS_FIELD_NAMES):
                    return True

        changes = container.get("changes")
        if isinstance(changes, Mapping):
            for key in changes:
                if _is_status_field_name(key):
                    return True

    return False


def _extract_status_from_changes(event: Mapping[str, Any]) -> str | None:
    for container in _walk_mappings(event):
        changes = container.get("changes")
        if not isinstance(changes, Mapping):
            continue

        for key, value in changes.items():
            if not _is_status_field_name(key):
                continue

            extracted = _extract_new_value(value)
            if extracted:
                return extracted

    return None


def _extract_new_value(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None

    if isinstance(value, Mapping):
        direct = _first_string_field(
            value,
            ("newValue", "new_value", "to", "after", "name", "title"),
        )
        if direct:
            return direct

        for nested_key in ("newValue", "new_value", "to", "after"):
            nested = value.get(nested_key)
            if isinstance(nested, Mapping):
                direct = _first_string_field(nested, ("name", "title"))
                if direct:
                    return direct

    return None


def _is_status_field_name(value: Any) -> bool:
    normalized = _normalize_label(value)
    return any(field_name in normalized for field_name in _STATUS_FIELD_NAMES)


def _walk_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for child in value.values():
            yield from _walk_mappings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_mappings(child)


def _iter_string_values(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, Mapping):
        for child in value.values():
            yield from _iter_string_values(child)
    elif isinstance(value, (list, tuple, set)):
        for child in value:
            yield from _iter_string_values(child)


def _first_string_field(container: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = container.get(key)
        if isinstance(value, str):
            stripped = value.strip()
            if stripped:
                return stripped
    return None


def _is_status_changed_label(value: Any) -> bool:
    normalized = _normalize_label(value)
    return normalized in {"status changed", "status change", "issue status changed"}


def _is_issue_update_label(value: Any) -> bool:
    normalized = _normalize_label(value)
    return normalized in {"update", "updated", "issue updated", "updated issue"}


def _normalize_label(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value.strip())
    spaced = re.sub(r"[^A-Za-z0-9]+", " ", spaced)
    return re.sub(r"\s+", " ", spaced).strip().casefold()


def _already_prefixed(title: str) -> bool:
    return title.casefold().startswith(TITLE_PREFIX.casefold())


def main() -> int:
    payload = json.load(sys.stdin)
    action = build_issue_title_update(payload)
    if action is not None:
        print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
