"""Build Linear issue title updates for Cursor research status changes.

The automation receives slightly different payload shapes depending on whether
the event comes from Cursor's trigger context or directly from Linear.  This
module keeps the public contract small: return an action describing the title
update when an issue moves to "to research", otherwise return ``None``.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_CAMEL_CASE_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_SEPARATORS = re.compile(r"[\s_\-]+")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action for research status transitions.

    The returned shape is intentionally serializable and side-effect free so the
    surrounding automation can decide how to apply it:

    ``{"action": "update_issue_title", "issueId": "...", "title": "..."}``
    """

    if not isinstance(event, Mapping):
        return None

    mappings = list(_iter_relevant_mappings(event))
    if not _is_status_change_event(mappings):
        return None

    status = _extract_status(mappings)
    if _normalize_text(status) != TARGET_STATUS:
        return None

    issue_id = _first_text(mappings, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_text(mappings, ("title", "name"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if _normalize_prefix(title).startswith(_normalize_prefix(PREFIX)):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _iter_relevant_mappings(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return mappings in precedence order for common Cursor/Linear payloads."""

    seen: set[int] = set()
    ordered: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if not isinstance(value, Mapping) or id(value) in seen:
            return
        seen.add(id(value))
        ordered.append(value)

    add(event)
    automation_info = event.get("automation_trigger_info")
    if isinstance(automation_info, Mapping):
        add(automation_info)
        add(automation_info.get("triggerContext"))

    add(event.get("triggerContext"))
    add(event.get("trigger_context"))
    add(event.get("webhook"))

    data = event.get("data")
    add(data)
    if isinstance(data, Mapping):
        add(data.get("issue"))
        add(data.get("node"))
        add(data.get("state"))
        add(data.get("workflowState"))

    add(event.get("issue"))
    add(event.get("node"))
    add(event.get("state"))
    add(event.get("workflowState"))

    return ordered


def _is_status_change_event(mappings: list[Mapping[str, Any]]) -> bool:
    trigger_values = _values_for_keys(
        mappings,
        ("trigger", "webhookType", "webhook_type", "action", "type", "eventType", "event_type"),
    )
    normalized_triggers = {_normalize_text(value) for value in trigger_values if value}

    direct_status_triggers = {
        "status changed",
        "status change",
        "state changed",
        "state change",
        "workflow state changed",
        "workflow state change",
    }
    if normalized_triggers & direct_status_triggers:
        return True

    update_triggers = {
        "update",
        "updated",
        "issue updated",
        "updated issue",
        "issue update",
        "update issue",
    }
    if normalized_triggers & update_triggers and _changed_fields_include_status(mappings):
        return True

    return _changed_fields_include_status(mappings) and bool(
        _values_for_keys(
            mappings,
            (
                "newStatus",
                "new_status",
                "toStatus",
                "to_status",
                "targetStatus",
                "target_status",
            ),
        )
    )


def _changed_fields_include_status(mappings: list[Mapping[str, Any]]) -> bool:
    status_fields = {"status", "state", "workflow state", "workflowstate", "workflow_state"}

    for mapping in mappings:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            fields = mapping.get(key)
            if isinstance(fields, str):
                values = [fields]
            elif isinstance(fields, list | tuple | set):
                values = list(fields)
            else:
                values = []

            for value in values:
                if _normalize_text(value) in status_fields:
                    return True

        changes = mapping.get("changes") or mapping.get("changed") or mapping.get("updatedFrom")
        if isinstance(changes, Mapping):
            for field in changes:
                if _normalize_text(field) in status_fields:
                    return True

    return False


def _extract_status(mappings: list[Mapping[str, Any]]) -> str | None:
    explicit = _first_text(
        mappings,
        (
            "newStatus",
            "new_status",
            "toStatus",
            "to_status",
            "targetStatus",
            "target_status",
            "statusName",
            "status_name",
        ),
    )
    if explicit:
        return explicit

    changed_status = _status_from_changes(mappings)
    if changed_status:
        return changed_status

    for mapping in mappings:
        for key in ("status", "state", "workflowState", "workflow_state"):
            value = mapping.get(key)
            text = _text_from_value(value)
            if text:
                return text

    return None


def _status_from_changes(mappings: list[Mapping[str, Any]]) -> str | None:
    for mapping in mappings:
        changes = mapping.get("changes") or mapping.get("changed")
        if not isinstance(changes, Mapping):
            continue

        for field in ("status", "state", "workflowState", "workflow_state"):
            change = changes.get(field)
            if not isinstance(change, Mapping):
                continue

            for key in ("to", "new", "after", "newValue", "new_value"):
                text = _text_from_value(change.get(key))
                if text:
                    return text

    return None


def _first_text(mappings: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for value in _values_for_keys(mappings, keys):
        text = _text_from_value(value)
        if text and text.strip():
            return text
    return None


def _values_for_keys(mappings: list[Mapping[str, Any]], keys: tuple[str, ...]) -> list[Any]:
    values: list[Any] = []
    for mapping in mappings:
        for key in keys:
            if key in mapping:
                values.append(mapping[key])
    return values


def _text_from_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        return _first_mapping_text(value, ("name", "title", "label", "id"))
    return str(value)


def _first_mapping_text(mapping: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _normalize_text(value: Any) -> str:
    text = _text_from_value(value) or ""
    text = _CAMEL_CASE_BOUNDARY.sub(" ", text)
    text = _SEPARATORS.sub(" ", text)
    return text.strip().casefold()


def _normalize_prefix(value: str) -> str:
    return value.strip().casefold()


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    print(json.dumps(action, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
