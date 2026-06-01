"""Build Linear issue title updates for research-status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_CHANGE_FIELDS = {
    "status",
    "status id",
    "state",
    "state id",
    "workflow state",
    "workflow state id",
    "workflow status",
    "workflowstate",
}
_STATUS_CHANGE_EVENTS = {
    "status change",
    "status changed",
    "status update",
    "status updated",
    "state change",
    "state changed",
    "state update",
    "state updated",
}
_ISSUE_UPDATE_EVENTS = {
    "issue update",
    "issue updated",
    "update",
    "updated",
    "updated issue",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title-update action when a Linear issue enters To Research."""
    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    status = _find_status(event)
    if _normalize(status) != TARGET_STATUS:
        return None

    issue_id = _string_value(
        _find_first(event, ("id", "issueId", "issue_id", "identifier"))
    )
    title = _string_value(_find_first(event, ("title", "name")))
    if issue_id is None or title is None:
        return None

    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _candidate_mappings(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    mappings: list[Mapping[str, Any]] = []

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        mappings.append(trigger_context)
        _append_nested_issue_mappings(mappings, trigger_context)

    mappings.append(event)
    _append_nested_issue_mappings(mappings, event)

    return mappings


def _append_nested_issue_mappings(
    mappings: list[Mapping[str, Any]], source: Mapping[str, Any]
) -> None:
    data = source.get("data")
    if isinstance(data, Mapping):
        mappings.append(data)
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            mappings.append(issue)

    issue = source.get("issue")
    if isinstance(issue, Mapping):
        mappings.append(issue)


def _find_first(event: Mapping[str, Any], keys: Sequence[str]) -> Any:
    for mapping in _candidate_mappings(event):
        for key in keys:
            value = mapping.get(key)
            if value is not None:
                return value
    return None


def _find_status(event: Mapping[str, Any]) -> Any:
    direct_value = _find_first(
        event,
        (
            "newStatus",
            "new_status",
            "newStatusName",
            "new_status_name",
            "status",
            "statusName",
            "status_name",
        ),
    )
    if direct_value is not None:
        return direct_value

    for mapping in _candidate_mappings(event):
        for key in ("state", "workflowState", "workflow_state"):
            value = mapping.get(key)
            if isinstance(value, Mapping):
                name = value.get("name")
                if name is not None:
                    return name
            elif value is not None:
                return value

    return None


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    event_names = []
    for mapping in _candidate_mappings(event):
        for key in ("trigger", "webhookType", "webhook_type", "eventType", "type", "action"):
            value = mapping.get(key)
            if value is not None:
                event_names.append(_normalize(value))

    if any(name in _STATUS_CHANGE_EVENTS for name in event_names):
        return True

    if any(name in _ISSUE_UPDATE_EVENTS for name in event_names):
        return _updated_fields_include_status(event)

    return False


def _updated_fields_include_status(event: Mapping[str, Any]) -> bool:
    for mapping in _candidate_mappings(event):
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            for field in _field_names(mapping.get(key)):
                if _normalize(field) in _STATUS_CHANGE_FIELDS:
                    return True

        for key in ("updatedFrom", "updated_from", "changedFrom", "changed_from"):
            fields = mapping.get(key)
            if isinstance(fields, Mapping):
                for field in fields:
                    if _normalize(field) in _STATUS_CHANGE_FIELDS:
                        return True

    return False


def _field_names(fields: Any) -> list[Any]:
    if isinstance(fields, Mapping):
        return list(fields.keys())
    if isinstance(fields, str):
        return [fields]
    if isinstance(fields, Sequence):
        return list(fields)
    return []


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def _string_value(value: Any) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    return text or None


def _normalize(value: Any) -> str:
    if value is None:
        return ""

    text = str(value).strip()
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def main() -> int:
    """Read a JSON payload from stdin and print the title update, if needed."""
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON payload: {exc}", file=sys.stderr)
        return 1

    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
