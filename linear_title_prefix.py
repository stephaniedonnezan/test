"""Build Linear issue title updates for research-status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


RESEARCH_STATUS = "to research"
TITLE_PREFIX = "Cursor researching"
STATUS_FIELD_NAMES = {"status", "state", "workflow state", "workflowstate"}
DIRECT_STATUS_CHANGE_EVENTS = {
    "status changed",
    "status change",
    "status updated",
    "state changed",
    "state change",
    "workflow state changed",
    "workflowstate changed",
}
GENERIC_UPDATE_EVENTS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue enters research.

    The handler accepts both Cursor automation trigger payloads and nested
    Linear-style webhook payloads. It intentionally returns a description of
    the update instead of mutating Linear directly, so callers can decide how to
    execute the action in their environment.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    new_status = _extract_new_status(event)
    if not _is_research_status(new_status):
        return None

    issue = _issue_mapping(event)
    issue_id = _extract_issue_id(issue, event)
    title = _extract_string(issue, "title", "name")

    if not issue_id or not title:
        return None

    clean_title = title.strip()
    if not clean_title or _has_research_prefix(clean_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {clean_title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    for value in _metadata_values(event, "trigger", "webhookType", "action", "type", "event"):
        normalized = _normalize(value)
        if normalized in DIRECT_STATUS_CHANGE_EVENTS:
            return True
        if normalized in GENERIC_UPDATE_EVENTS and _payload_mentions_status_field(event):
            return True

    return _payload_mentions_status_field(event)


def _extract_new_status(event: Mapping[str, Any]) -> str | None:
    for mapping in _mappings(event):
        status = _extract_string(
            mapping,
            "newStatus",
            "new_status",
            "toStatus",
            "to_status",
            "targetStatus",
            "target_status",
            "statusName",
            "status_name",
            "stateName",
            "state_name",
            "workflowStateName",
            "workflow_state_name",
        )
        if status:
            return status

    changed_status = _extract_status_from_changes(event)
    if changed_status:
        return changed_status

    issue = _issue_mapping(event)
    return _extract_status_name(issue) or _extract_status_name(event)


def _extract_status_from_changes(event: Mapping[str, Any]) -> str | None:
    for mapping in _mappings(event):
        for key in ("changes", "updatedFields", "changedFields"):
            value = mapping.get(key)
            status = _status_from_change_container(value)
            if status:
                return status
    return None


def _status_from_change_container(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key, change in value.items():
            if not _is_status_field(key):
                continue
            status = _status_from_change(change)
            if status:
                return status
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, str) and _is_status_field(item):
                continue

            if not isinstance(item, Mapping):
                continue

            field_name = _extract_string(item, "field", "fieldName", "name", "key")
            if field_name and not _is_status_field(field_name):
                continue

            status = _status_from_change(item)
            if status:
                return status

    return None


def _status_from_change(change: Any) -> str | None:
    if isinstance(change, str):
        return change

    if not isinstance(change, Mapping):
        return None

    for key in ("newValue", "new_value", "to", "after", "current", "value", "name"):
        value = change.get(key)
        status = _string_or_name(value)
        if status:
            return status

    return _extract_status_name(change)


def _payload_mentions_status_field(event: Mapping[str, Any]) -> bool:
    for mapping in _mappings(event):
        for key in ("updatedFields", "changedFields"):
            if _container_mentions_status_field(mapping.get(key)):
                return True

        changes = mapping.get("changes")
        if isinstance(changes, Mapping):
            if any(_is_status_field(key) for key in changes):
                return True
        elif _container_mentions_status_field(changes):
            return True

    return False


def _container_mentions_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)

    if isinstance(value, list):
        for item in value:
            if isinstance(item, str) and _is_status_field(item):
                return True
            if isinstance(item, Mapping):
                field_name = _extract_string(item, "field", "fieldName", "name", "key")
                if field_name and _is_status_field(field_name):
                    return True

    if isinstance(value, Mapping):
        return any(_is_status_field(key) for key in value)

    return False


def _issue_mapping(event: Mapping[str, Any]) -> Mapping[str, Any]:
    for mapping in _mappings(event):
        for key in ("issue", "data"):
            nested = mapping.get(key)
            if _looks_like_issue(nested):
                return nested

    for mapping in _mappings(event):
        if _looks_like_issue(mapping):
            return mapping

    return event


def _looks_like_issue(value: Any) -> bool:
    return isinstance(value, Mapping) and bool(_extract_string(value, "title", "name"))


def _extract_issue_id(issue: Mapping[str, Any], event: Mapping[str, Any]) -> str | None:
    issue_id = _extract_string(issue, "issueId", "issue_id", "identifier", "key", "id")
    if issue_id:
        return issue_id

    for mapping in _mappings(event):
        issue_id = _extract_string(mapping, "issueId", "issue_id", "identifier", "key")
        if issue_id:
            return issue_id

    return None


def _extract_status_name(mapping: Mapping[str, Any]) -> str | None:
    direct_status = _extract_string(mapping, "status", "state", "workflowState")
    if direct_status:
        return direct_status

    for key in ("status", "state", "workflowState", "workflow_state"):
        value = mapping.get(key)
        status = _string_or_name(value)
        if status:
            return status

    return None


def _metadata_values(event: Mapping[str, Any], *keys: str) -> list[str]:
    values: list[str] = []
    for mapping in _mappings(event):
        for key in keys:
            value = mapping.get(key)
            if isinstance(value, str):
                values.append(value)
    return values


def _mappings(value: Any) -> list[Mapping[str, Any]]:
    mappings: list[Mapping[str, Any]] = []

    def visit(item: Any) -> None:
        if not isinstance(item, Mapping):
            return
        mappings.append(item)
        for key in ("triggerContext", "data", "issue"):
            visit(item.get(key))

    visit(value)
    return mappings


def _extract_string(mapping: Mapping[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = mapping.get(key)
        text = _string_or_name(value)
        if text:
            return text
    return None


def _string_or_name(value: Any) -> str | None:
    if isinstance(value, str):
        return value

    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            nested = value.get(key)
            if isinstance(nested, str):
                return nested

    return None


def _is_research_status(value: str | None) -> bool:
    return _normalize(value) == RESEARCH_STATUS


def _is_status_field(value: Any) -> bool:
    return _normalize(value) in STATUS_FIELD_NAMES


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def _normalize(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return re.sub(r"[^a-z0-9]+", " ", spaced.lower()).strip()


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        json.dump(update, sys.stdout)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
