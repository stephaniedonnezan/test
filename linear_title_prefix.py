"""Build title-update actions for Linear issues moved to research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = frozenset({"status", "state", "workflowstate", "workflow_state"})
DIRECT_STATUS_CHANGE_EVENTS = frozenset({"statuschanged", "statuschange", "statusupdated", "statusupdate"})
GENERIC_UPDATE_EVENTS = frozenset({"update", "updated", "issueupdated", "updatedissue"})


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title-update action when a Linear issue moves to "to research"."""
    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    if _normalize_name(_extract_new_status(event)) != _normalize_name(TARGET_STATUS):
        return None

    issue_id = _extract_issue_id(event)
    title = _extract_title(event)
    if not issue_id or not title:
        return None

    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    event_names = {_normalize_name(value) for value in _iter_event_name_values(event)}
    event_names.discard("")

    if event_names & DIRECT_STATUS_CHANGE_EVENTS:
        return True

    if event_names & GENERIC_UPDATE_EVENTS:
        return _updated_fields_include_status(event) or _changes_include_status(event)

    return False


def _extract_new_status(event: Mapping[str, Any]) -> Any:
    for container in _candidate_mappings(event):
        for key in ("newStatus", "new_status", "statusName", "status_name"):
            value = container.get(key)
            if value:
                return value

    for change in _iter_change_mappings(event):
        for key in ("newStatus", "new_status", "to", "after", "newValue", "new_value"):
            value = change.get(key)
            if value:
                return _name_from_value(value)

    for container in _candidate_mappings(event):
        for key in ("status", "state", "workflowState", "workflow_state"):
            value = container.get(key)
            if value:
                return _name_from_value(value)

    return None


def _extract_issue_id(event: Mapping[str, Any]) -> str | None:
    for container in _candidate_mappings(event):
        for key in ("id", "issueId", "issue_id", "identifier", "key"):
            value = container.get(key)
            if value is not None:
                issue_id = str(value).strip()
                if issue_id:
                    return issue_id
    return None


def _extract_title(event: Mapping[str, Any]) -> str | None:
    for container in _candidate_mappings(event):
        value = container.get("title")
        if value is not None:
            title = str(value).strip()
            if title:
                return title
    return None


def _candidate_mappings(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    candidates: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in candidates:
            candidates.append(value)

    add(event)

    for key in ("triggerContext", "data", "issue"):
        value = event.get(key)
        add(value)
        if isinstance(value, Mapping):
            add(value.get("issue"))
            add(value.get("triggerContext"))
            data = value.get("data")
            add(data)
            if isinstance(data, Mapping):
                add(data.get("issue"))

    return candidates


def _iter_event_name_values(event: Mapping[str, Any]) -> Iterable[Any]:
    for container in _candidate_mappings(event):
        for key in ("trigger", "webhookType", "action", "type"):
            value = container.get(key)
            if value:
                yield value


def _updated_fields_include_status(event: Mapping[str, Any]) -> bool:
    for container in _candidate_mappings(event):
        updated_fields = container.get("updatedFields") or container.get("updated_fields")
        if updated_fields is None:
            continue

        if isinstance(updated_fields, str):
            fields = re.split(r"[, ]+", updated_fields)
        elif isinstance(updated_fields, Iterable):
            fields = updated_fields
        else:
            fields = ()

        for field in fields:
            if _normalize_field_name(field) in STATUS_FIELDS:
                return True

    return False


def _changes_include_status(event: Mapping[str, Any]) -> bool:
    for change in _iter_change_mappings(event):
        field = change.get("field") or change.get("fieldName") or change.get("field_name") or change.get("name")
        if _normalize_field_name(field) in STATUS_FIELDS:
            return True

    return False


def _iter_change_mappings(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    for container in _candidate_mappings(event):
        changes = container.get("changes") or container.get("change")

        if isinstance(changes, Mapping):
            for key, value in changes.items():
                if _normalize_field_name(key) in STATUS_FIELDS and isinstance(value, Mapping):
                    yield value
                elif _normalize_field_name(key) in STATUS_FIELDS:
                    yield {"field": key, "newValue": value}
                elif isinstance(value, Mapping):
                    yield value
        elif isinstance(changes, Iterable) and not isinstance(changes, (str, bytes)):
            for value in changes:
                if isinstance(value, Mapping):
                    yield value


def _name_from_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return value.get("name") or value.get("title") or value.get("status") or value.get("id")
    return value


def _normalize_name(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def _normalize_field_name(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"[^a-z0-9]+", "", str(value).lower())


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update:
        json.dump(update, sys.stdout)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
