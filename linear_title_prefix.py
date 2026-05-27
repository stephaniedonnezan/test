"""Build Linear issue-title updates for Cursor research automation events."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow_state"}
_STATUS_CHANGE_TRIGGERS = {
    "status changed",
    "status change",
    "statuschanged",
    "statuschange",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
}
_ISSUE_UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title-update action when an issue moves to research."""

    if not isinstance(event, Mapping):
        return None

    mappings = list(_candidate_mappings(event))
    if not _is_status_change(mappings):
        return None

    status = _find_status(mappings)
    if _normalize_text(status) != TARGET_STATUS:
        return None

    title = _find_string(mappings, ("title", "name"))
    issue_id = _find_issue_id(mappings)
    if not title or not issue_id:
        return None

    title = title.strip()
    if _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _candidate_mappings(event: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    """Return likely payload locations from most-specific to least-specific."""

    candidates: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in candidates:
            candidates.append(value)

    trigger_context = event.get("triggerContext")
    add(trigger_context)

    data = _get_mapping(event, "data")
    issue = _get_mapping(event, "issue")
    add(_get_mapping(data, "issue"))
    add(issue)
    add(data)

    if isinstance(trigger_context, Mapping):
        trigger_data = _get_mapping(trigger_context, "data")
        trigger_issue = _get_mapping(trigger_context, "issue")
        add(_get_mapping(trigger_data, "issue"))
        add(trigger_issue)
        add(trigger_data)

    add(event)
    return tuple(candidates)


def _is_status_change(mappings: list[Mapping[str, Any]]) -> bool:
    for mapping in mappings:
        for key in ("trigger", "action", "type", "webhookType", "event", "eventType"):
            normalized = _normalize_text(mapping.get(key))
            if normalized in _STATUS_CHANGE_TRIGGERS:
                return True
            if normalized in _ISSUE_UPDATE_TRIGGERS and _updated_status_fields(mappings):
                return True
    return False


def _updated_status_fields(mappings: list[Mapping[str, Any]]) -> bool:
    for mapping in mappings:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            value = mapping.get(key)
            fields = value if isinstance(value, (list, tuple, set)) else (value,)
            for field in fields:
                if _normalize_field_name(field) in _STATUS_FIELD_NAMES:
                    return True

        updated_from = mapping.get("updatedFrom") or mapping.get("updated_from")
        if isinstance(updated_from, Mapping):
            for field in updated_from:
                if _normalize_field_name(field) in _STATUS_FIELD_NAMES:
                    return True

    return False


def _find_status(mappings: list[Mapping[str, Any]]) -> str | None:
    direct_keys = (
        "newStatus",
        "new_status",
        "statusName",
        "status_name",
        "stateName",
        "state_name",
        "workflowStateName",
        "workflow_state_name",
    )
    status = _find_string(mappings, direct_keys)
    if status:
        return status

    for mapping in mappings:
        for key in ("status", "state", "workflowState", "workflow_state"):
            value = mapping.get(key)
            if isinstance(value, str):
                return value
            if isinstance(value, Mapping):
                name = value.get("name") or value.get("title")
                if isinstance(name, str):
                    return name
    return None


def _find_issue_id(mappings: list[Mapping[str, Any]]) -> str | None:
    preferred = _find_string(mappings, ("issueId", "issue_id", "identifier"))
    if preferred:
        return preferred

    for mapping in mappings:
        value = mapping.get("id")
        if isinstance(value, str) and value.strip():
            return value
    return None


def _find_string(mappings: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for mapping in mappings:
        for key in keys:
            value = mapping.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _get_mapping(mapping: Mapping[str, Any] | None, key: str) -> Mapping[str, Any] | None:
    if not isinstance(mapping, Mapping):
        return None
    value = mapping.get(key)
    return value if isinstance(value, Mapping) else None


def _normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    words = re.sub(r"[^a-zA-Z0-9]+", " ", spaced).casefold().strip()
    return re.sub(r"\s+", " ", words)


def _normalize_field_name(value: Any) -> str:
    return _normalize_text(value).replace(" ", "")


def _has_prefix(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())


def main() -> int:
    event = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(event), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
