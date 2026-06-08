"""Build Linear issue title updates for Cursor research-status automations."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}
ID_FIELDS = ("id", "issueId", "issue_id", "identifier", "key", "uuid")


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to To Research."""

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    if _normalize_status(_target_status(event)) != _normalize_status(TARGET_STATUS):
        return None

    issue_id = _issue_id(event)
    title = _issue_title(event)
    if not issue_id or not title:
        return None

    if title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def handle_issue_status_changed(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Compatibility alias for automation entrypoints named after the trigger."""

    return build_issue_title_update(event)


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    values = [
        _normalize_token(value)
        for source in _context_sources(event)
        for key in ("trigger", "webhookType", "action", "type", "eventType")
        if (value := source.get(key)) is not None
    ]

    if any(value in {"statuschanged", "statuschange"} for value in values):
        return True

    if any(value in {"update", "updated", "issueupdated", "updatedissue", "issueupdate"} for value in values):
        return _has_status_change_evidence(event)

    return _has_status_change_evidence(event) and _target_status(event) is not None


def _has_status_change_evidence(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized_key = _normalize_token(key)
            if normalized_key in {"updatedfields", "changedfields"} and _contains_status_field(child):
                return True
            if normalized_key in {"changes", "changed", "updatedfrom"} and _contains_status_field(child):
                return True
            if isinstance(child, (Mapping, list, tuple)) and _has_status_change_evidence(child):
                return True

    if isinstance(value, (list, tuple)):
        return any(_has_status_change_evidence(item) for item in value)

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_token(value) in STATUS_FIELDS

    if isinstance(value, Mapping):
        return any(_normalize_token(key) in STATUS_FIELDS or _contains_status_field(child) for key, child in value.items())

    if isinstance(value, Iterable):
        return any(_contains_status_field(item) for item in value)

    return False


def _target_status(event: Mapping[str, Any]) -> str | None:
    for source in _context_sources(event):
        for key in ("newStatus", "new_status", "toStatus", "to_status", "statusName", "status_name"):
            if status := _string_value(source.get(key)):
                return status

    if status := _status_from_changes(event):
        return status

    for source in _context_sources(event):
        if status := _string_value(source.get("status")):
            return status
        if status := _name_from_mapping(source.get("state")):
            return status
        if status := _name_from_mapping(source.get("workflowState")):
            return status
        if status := _name_from_mapping(source.get("workflow_state")):
            return status

    return None


def _status_from_changes(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized_key = _normalize_token(key)
            if normalized_key == "updatedfrom":
                continue

            if normalized_key in STATUS_FIELDS:
                if status := _new_value_from_change(child):
                    return status

            if isinstance(child, (Mapping, list, tuple)):
                if status := _status_from_changes(child):
                    return status

    if isinstance(value, (list, tuple)):
        for item in value:
            if status := _status_from_changes(item):
                return status

    return None


def _new_value_from_change(value: Any) -> str | None:
    if status := _string_value(value):
        return status

    if isinstance(value, Mapping):
        for key in ("newValue", "new_value", "to", "after", "value", "name"):
            if status := _string_value(value.get(key)):
                return status
            if status := _name_from_mapping(value.get(key)):
                return status

    return None


def _issue_id(event: Mapping[str, Any]) -> str | None:
    for source in _issue_sources(event):
        for key in ID_FIELDS:
            if issue_id := _string_value(source.get(key)):
                return issue_id
    return None


def _issue_title(event: Mapping[str, Any]) -> str | None:
    for source in _issue_sources(event):
        if title := _string_value(source.get("title")):
            return title
    return None


def _issue_sources(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    sources: list[Mapping[str, Any]] = []
    trigger_context = event.get("triggerContext")
    data = event.get("data")

    if isinstance(trigger_context, Mapping):
        sources.append(trigger_context)
    if isinstance(data, Mapping):
        for key in ("issue", "node"):
            if isinstance(data.get(key), Mapping):
                sources.append(data[key])
    if isinstance(event.get("issue"), Mapping):
        sources.append(event["issue"])
    if isinstance(data, Mapping):
        sources.append(data)
    sources.append(event)

    return sources


def _context_sources(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    sources = [event]
    for key in ("triggerContext", "data", "issue"):
        if isinstance(event.get(key), Mapping):
            sources.append(event[key])
    data = event.get("data")
    if isinstance(data, Mapping):
        for key in ("issue", "node"):
            if isinstance(data.get(key), Mapping):
                sources.append(data[key])
    return sources


def _name_from_mapping(value: Any) -> str | None:
    if isinstance(value, Mapping):
        return _string_value(value.get("name"))
    return None


def _string_value(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        if stripped:
            return stripped
    return None


def _normalize_status(value: str | None) -> str:
    if value is None:
        return ""
    return _normalize_token(value)


def _normalize_token(value: Any) -> str:
    text = str(value)
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def main() -> int:
    event = json.load(sys.stdin)
    result = build_issue_title_update(event)
    print(json.dumps(result, indent=2, sort_keys=True) if result else "null")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
