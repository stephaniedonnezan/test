"""Build Linear issue title updates for research-status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_DIRECT_STATUS_TRIGGERS = {
    "status changed",
    "status change",
    "statuschanged",
    "state changed",
    "state change",
    "workflow state changed",
    "workflowstate changed",
}
_UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}
_STATUS_FIELD_NAMES = {
    "status",
    "status id",
    "status name",
    "state",
    "state id",
    "state name",
    "workflow state",
    "workflow state id",
    "workflow state name",
    "workflowstate",
    "workflowstate id",
    "workflowstate name",
}
_NEW_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "toStatus",
    "to_status",
    "statusName",
    "status_name",
    "newState",
    "new_state",
)
_FALLBACK_STATUS_KEYS = ("status", "state", "workflowState", "workflow_state")
_TITLE_KEYS = ("title", "name")
_ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "key")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear issue-title update action for a research status change.

    The automation trigger can arrive as a flat Cursor trigger context or as a
    nested Linear webhook payload. This function keeps the output small and
    side-effect free so the caller can decide how to submit the update.
    """

    if not isinstance(event, Mapping):
        return None

    sources = _collect_sources(event)
    if not _is_status_change_event(sources):
        return None

    if _normalize_text(_first_status_value(sources)) != TARGET_STATUS:
        return None

    issue_id = _first_issue_id(sources)
    title = _first_string(sources, _TITLE_KEYS)
    if not issue_id or not title:
        return None

    title = title.strip()
    if not title or _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _collect_sources(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    sources: list[Mapping[str, Any]] = []
    seen: set[int] = set()

    def visit(value: Any) -> None:
        if not isinstance(value, Mapping):
            return
        identity = id(value)
        if identity in seen:
            return
        seen.add(identity)
        sources.append(value)

        for key in ("triggerContext", "payload", "data", "issue", "node"):
            nested = value.get(key)
            if isinstance(nested, Mapping):
                visit(nested)

    visit(event)
    return sources


def _is_status_change_event(sources: Iterable[Mapping[str, Any]]) -> bool:
    source_list = list(sources)
    trigger_values: list[str] = []

    for source in source_list:
        for key in ("trigger", "webhookType", "action", "type", "event", "eventType"):
            value = source.get(key)
            if isinstance(value, str):
                trigger_values.append(value)

    normalized_triggers = {_normalize_text(value) for value in trigger_values}
    if normalized_triggers & _DIRECT_STATUS_TRIGGERS:
        return True

    if normalized_triggers & _UPDATE_TRIGGERS:
        return _has_status_field_change(source_list)

    return False


def _has_status_field_change(sources: Iterable[Mapping[str, Any]]) -> bool:
    for source in sources:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            if _contains_status_field(source.get(key)):
                return True

        changes = source.get("changes")
        if isinstance(changes, Mapping):
            if any(_is_status_field(field) for field in changes):
                return True
        elif _contains_status_field(changes):
            return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)
    if isinstance(value, Mapping):
        return any(_is_status_field(key) or _contains_status_field(item) for key, item in value.items())
    if isinstance(value, Iterable):
        return any(_contains_status_field(item) for item in value)
    return False


def _is_status_field(value: Any) -> bool:
    return isinstance(value, str) and _normalize_text(value) in _STATUS_FIELD_NAMES


def _first_status_value(sources: Iterable[Mapping[str, Any]]) -> str | None:
    source_list = list(sources)

    for source in source_list:
        value = _extract_first_value(source, _NEW_STATUS_KEYS)
        if value:
            return value

    changed_value = _status_value_from_changes(source_list)
    if changed_value:
        return changed_value

    for source in source_list:
        value = _extract_first_value(source, _FALLBACK_STATUS_KEYS)
        if value:
            return value

    return None


def _status_value_from_changes(sources: Iterable[Mapping[str, Any]]) -> str | None:
    for source in sources:
        changes = source.get("changes")
        if not isinstance(changes, Mapping):
            continue

        for field, change in changes.items():
            if not _is_status_field(field):
                continue

            if isinstance(change, Mapping):
                value = _extract_first_value(
                    change,
                    ("newValue", "new_value", "to", "after", "name", "value"),
                )
                if value:
                    return value
            elif isinstance(change, str):
                return change

    return None


def _first_string(sources: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for source in sources:
        value = _extract_first_value(source, keys)
        if value:
            return value
    return None


def _first_issue_id(sources: Iterable[Mapping[str, Any]]) -> str | None:
    source_list = list(sources)
    return _first_string(source_list, _ISSUE_ID_KEYS) or _first_string(source_list, ("id",))


def _extract_first_value(source: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for key in keys:
        value = source.get(key)
        if isinstance(value, str) and value.strip():
            return value
        if isinstance(value, Mapping):
            nested_name = _extract_first_value(value, ("name", "title", "identifier", "key", "id"))
            if nested_name:
                return nested_name
    return None


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def _normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    value = re.sub(r"[^A-Za-z0-9]+", " ", value)
    return " ".join(value.lower().split())


def main() -> int:
    payload = json.load(sys.stdin)
    action = build_issue_title_update(payload)
    if action is not None:
        json.dump(action, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
