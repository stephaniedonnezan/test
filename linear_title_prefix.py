"""Build Linear issue title updates for research-status automations."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"

_CONTAINER_KEYS = (
    "automation_trigger_info",
    "triggerContext",
    "trigger_context",
    "payload",
    "data",
    "issue",
)
_TRIGGER_KEYS = ("trigger", "webhookType", "webhook_type", "action", "type")
_STATUS_KEYS = {
    "status",
    "state",
    "workflowstate",
    "workflow state",
    "workflow status",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title-update instruction when an issue moves to research."""
    if not isinstance(event, Mapping):
        return None

    payload = _flatten_event(event)
    if not _is_status_change_event(event):
        return None
    if _normalize_label(_changed_status(event, payload)) != TARGET_STATUS:
        return None

    issue_id = _as_text(
        _first_present(payload, "issueId", "issue_id", "identifier", "key", "id")
    )
    title = _as_text(_first_present(payload, "title", "name"))
    if not issue_id or not title:
        return None

    if _has_prefix(title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _flatten_event(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common webhook nesting levels, keeping outer metadata last."""
    flattened: dict[str, Any] = {}
    for source in reversed(list(_mapping_sources(event))):
        flattened.update(_normalized_payload(source))
    return flattened


def _mapping_sources(payload: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    yield payload

    for key in _CONTAINER_KEYS:
        nested = payload.get(key)
        if isinstance(nested, Mapping):
            yield from _mapping_sources(nested)


def _normalized_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    fields = dict(payload)
    for key in ("status", "state", "workflowState", "workflow_state"):
        value = fields.get(key)
        if isinstance(value, Mapping):
            name = _first_present(value, "name", "title")
            if name is not None:
                fields[key] = name

    return fields


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    triggers = {
        _normalize_label(source.get(key))
        for source in _mapping_sources(event)
        for key in _TRIGGER_KEYS
        if source.get(key) is not None
    }
    if triggers & {
        "status changed",
        "statuschanged",
        "status change",
        "issue status changed",
        "state changed",
        "workflow state changed",
        "workflowstate changed",
    }:
        return True

    update_triggers = {
        "update",
        "updated",
        "issue updated",
        "updated issue",
        "issue update",
    }
    return bool(triggers & update_triggers) and _status_field_was_updated(event)


def _status_field_was_updated(event: Mapping[str, Any]) -> bool:
    for source in _mapping_sources(event):
        updated_fields = _first_present(
            source,
            "updatedFields",
            "updated_fields",
            "changedFields",
            "changed_fields",
        )
        if any(_is_status_field(field) for field in _iter_values(updated_fields)):
            return True

        changes = source.get("changes")
        if isinstance(changes, Mapping) and any(
            _is_status_field(field) for field in changes.keys()
        ):
            return True

    return False


def _changed_status(event: Mapping[str, Any], payload: Mapping[str, Any]) -> Any:
    explicit = _first_present(
        payload,
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "newWorkflowState",
        "new_workflow_state",
        "statusName",
        "status_name",
    )
    if explicit is not None:
        return explicit

    from_changes = _status_from_changes(event)
    if from_changes is not None:
        return from_changes

    return _first_present(payload, "status", "state", "workflowState", "workflow_state")


def _status_from_changes(event: Mapping[str, Any]) -> Any:
    for source in _mapping_sources(event):
        changes = source.get("changes")
        if not isinstance(changes, Mapping):
            continue

        for field, change in changes.items():
            if not _is_status_field(field):
                continue

            if isinstance(change, Mapping):
                value = _first_present(
                    change,
                    "to",
                    "new",
                    "newValue",
                    "new_value",
                    "after",
                    "current",
                    "name",
                )
                if value is not None:
                    return value
            else:
                return change

    return None


def _first_present(payload: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        value = payload.get(key)
        if value is not None:
            return value
    return None


def _iter_values(value: Any) -> Iterable[Any]:
    if isinstance(value, str) or not isinstance(value, Iterable):
        return (value,)
    return value


def _is_status_field(value: Any) -> bool:
    return _normalize_label(value) in _STATUS_KEYS


def _as_text(value: Any) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    return text or None


def _normalize_label(value: Any) -> str:
    if isinstance(value, Mapping):
        value = _first_present(value, "name", "title")
    if value is None:
        return ""

    text = str(value).strip()
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^a-zA-Z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def _has_prefix(title: str) -> bool:
    return title.strip().lower().startswith(TITLE_PREFIX.lower())


def _main() -> int:
    result = build_issue_title_update(json.load(sys.stdin))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
