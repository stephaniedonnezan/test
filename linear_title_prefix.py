"""Build Linear issue title updates for research-status transitions.

The automation receives webhook payloads in a few shapes depending on whether
they come from Cursor's trigger context or directly from Linear. This module
normalizes those variants and returns the title update action expected by the
automation runner.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"

_STATUS_FIELD_NAMES = {"status", "state", "workflow state", "workflowstate"}
_STATUS_CHANGE_TRIGGERS = {
    "status changed",
    "status change",
    "status updated",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
}
_GENERIC_UPDATE_TRIGGERS = {
    "issue updated",
    "updated issue",
    "update",
    "updated",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return an issue-title update when a Linear issue moves to To Research.

    The returned payload is intentionally small and side-effect free so callers
    can decide how to apply it:

    ``{"action": "update_issue_title", "issueId": "...", "title": "..."}``
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _context_layers(event)
    if not _is_status_change_event(contexts):
        return None

    status = _extract_new_status(contexts)
    if _normalize_text(status) != TARGET_STATUS:
        return None

    issue_id = _extract_issue_id(contexts)
    title = _extract_title(contexts)
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_prefix(title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _context_layers(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return likely issue/webhook dictionaries from outermost to innermost."""

    layers: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in layers:
            layers.append(value)

    add(event)
    for key in ("triggerContext", "trigger_context", "data", "issue"):
        nested = event.get(key)
        add(nested)
        if isinstance(nested, Mapping):
            for nested_key in ("issue", "data", "triggerContext", "trigger_context"):
                add(nested.get(nested_key))

    trigger_context = event.get("triggerContext") or event.get("trigger_context")
    if isinstance(trigger_context, Mapping):
        data = trigger_context.get("data")
        add(data)
        if isinstance(data, Mapping):
            add(data.get("issue"))

    data = event.get("data")
    if isinstance(data, Mapping):
        add(data.get("issue"))

    return layers


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    trigger_values = []
    has_status_field_marker = False

    for context in contexts:
        for key in ("trigger", "webhookType", "action", "type", "eventType", "event_type"):
            value = context.get(key)
            if isinstance(value, str):
                trigger_values.append(_normalize_text(value))

        if _has_status_field_marker(context):
            has_status_field_marker = True

    if any(value in _STATUS_CHANGE_TRIGGERS for value in trigger_values):
        return True

    return has_status_field_marker and any(
        value in _GENERIC_UPDATE_TRIGGERS for value in trigger_values
    )


def _has_status_field_marker(context: Mapping[str, Any]) -> bool:
    for key in (
        "updatedFields",
        "updated_fields",
        "changedFields",
        "changed_fields",
        "changes",
        "changed",
        "updated",
        "updatedFrom",
        "updated_from",
    ):
        fields = {_normalize_text(field) for field in _field_names(context.get(key))}
        if fields & _STATUS_FIELD_NAMES:
            return True

    return False


def _field_names(value: Any) -> set[str]:
    if isinstance(value, str):
        return {value}

    if isinstance(value, Mapping):
        names = set(value.keys())
        for key in ("field", "fieldName", "field_name", "name", "property"):
            nested_value = value.get(key)
            if isinstance(nested_value, str):
                names.add(nested_value)

        for nested_value in value.values():
            names.update(_field_names(nested_value))

        return names

    if isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray)):
        names: set[str] = set()
        for item in value:
            names.update(_field_names(item))
        return names

    return set()


def _extract_new_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    status_keys = (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "newWorkflowState",
        "new_workflow_state",
        "status",
        "state",
        "workflowState",
        "workflow_state",
    )

    for context in contexts:
        for key in status_keys:
            status = _string_or_named_value(context.get(key))
            if status:
                return status

    return None


def _extract_issue_id(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        for key in ("issueId", "issue_id", "identifier", "key", "id"):
            issue_id = context.get(key)
            if isinstance(issue_id, str) and issue_id.strip():
                return issue_id

    return None


def _extract_title(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        title = context.get("title")
        if isinstance(title, str) and title.strip():
            return title

    return None


def _string_or_named_value(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value

    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            nested_value = value.get(key)
            if isinstance(nested_value, str) and nested_value.strip():
                return nested_value

    return None


def _has_prefix(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())


def _normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    with_camel_boundaries = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value.strip())
    words = re.sub(r"[^A-Za-z0-9]+", " ", with_camel_boundaries)
    return re.sub(r"\s+", " ", words).strip().casefold()


def main() -> int:
    event = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(event), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
