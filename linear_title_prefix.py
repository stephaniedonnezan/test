"""Build Linear issue title updates for Cursor research automation triggers."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update when an issue moves into research status.

    Cursor and Linear payloads can be flat or nested under ``triggerContext``,
    ``data.issue``, or ``issue``. The handler keeps updates idempotent by
    skipping titles that already start with the research prefix.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    if _normalize(_first_value(event, ("newStatus", "new_status", "status", "state", "workflowState"))) != TARGET_STATUS:
        return None

    issue_id = _first_value(event, ("id", "issueId", "issue_id", "identifier"))
    title = _first_value(event, ("title", "name"))

    if not isinstance(issue_id, str) or not issue_id.strip():
        return None

    if not isinstance(title, str) or not title.strip():
        return None

    clean_title = title.strip()
    if clean_title.casefold().startswith(TITLE_PREFIX.casefold()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {clean_title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    event_name = _first_value(
        event,
        ("trigger", "webhookType", "webhook_type", "action", "type", "eventType", "event_type"),
    )
    normalized_event_name = _normalize(event_name)

    if normalized_event_name in {"status changed", "status change", "status updated"}:
        return True

    updated_fields = _first_value(event, ("updatedFields", "updated_fields", "changedFields", "changed_fields"))
    has_status_field_change = _sequence_contains_status_field(updated_fields)

    if normalized_event_name in {"issue updated", "updated issue"} and has_status_field_change:
        return True

    status_value = _first_value(event, ("newStatus", "new_status", "status", "state", "workflowState"))
    return has_status_field_change and status_value is not None


def _first_value(event: Mapping[str, Any], keys: Sequence[str]) -> Any:
    for source in _candidate_sources(event):
        value = _value_from_source(source, keys)
        if value is not None:
            return value

    return None


def _candidate_sources(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    sources: list[Mapping[str, Any]] = [event]

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        sources.extend(_source_with_nested_issue(trigger_context))

    data = event.get("data")
    if isinstance(data, Mapping):
        sources.extend(_source_with_nested_issue(data))

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        sources.append(issue)

    return sources


def _source_with_nested_issue(source: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    sources: list[Mapping[str, Any]] = [source]

    data = source.get("data")
    if isinstance(data, Mapping):
        sources.append(data)
        issue_from_data = data.get("issue")
        if isinstance(issue_from_data, Mapping):
            sources.append(issue_from_data)

    issue = source.get("issue")
    if isinstance(issue, Mapping):
        sources.append(issue)

    return sources


def _value_from_source(source: Mapping[str, Any], keys: Sequence[str]) -> Any:
    for key in keys:
        if key not in source:
            continue

        value = source[key]
        if key in {"state", "workflowState"} and isinstance(value, Mapping):
            return value.get("name")

        return value

    return None


def _sequence_contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize(value) in {"status", "state", "workflow state"}

    if isinstance(value, Mapping):
        return any(_normalize(key) in {"status", "state", "workflow state"} for key in value)

    if not isinstance(value, Sequence) or isinstance(value, (bytes, bytearray)):
        return False

    return any(_normalize(item) in {"status", "state", "workflow state"} for item in value)


def _normalize(value: Any) -> str:
    if isinstance(value, Mapping):
        value = value.get("name")

    if value is None:
        return ""

    text = str(value)
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[_\-]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().casefold()
