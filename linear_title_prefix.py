"""Build Linear issue title updates for research status transitions.

The automation receives slightly different payload shapes depending on whether
it is invoked from Cursor trigger metadata or a raw Linear webhook. This module
normalizes those shapes and returns a small action object for the caller to
apply to Linear.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_NEW_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "toStatus",
    "to_status",
    "statusName",
    "status_name",
)
_EVENT_KEYS = ("trigger", "event", "action", "type", "webhookType", "webhook_type")
_UPDATED_FIELD_KEYS = (
    "updatedFields",
    "updated_fields",
    "changedFields",
    "changed_fields",
    "updatedFrom",
    "updated_from",
)
_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "stateid",
    "workflowstate",
    "workflowstateid",
    "workflowstateid",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action for a transition to research.

    The return value is intentionally side-effect free so callers can decide how
    to execute the Linear API mutation. ``None`` means the event should be
    ignored.
    """

    if not isinstance(event, Mapping):
        return None

    sources = _payload_sources(event)
    if not _is_status_change_event(event, sources):
        return None

    new_status = _status_from_event(event, sources)
    if _normalize_words(new_status) != TARGET_STATUS:
        return None

    issue_id = _first_text(sources, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_text(sources, ("title", "name"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _payload_sources(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return payload sections in issue-data preference order."""

    sources: list[Mapping[str, Any]] = []

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        sources.append(trigger_context)

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        sources.append(issue)

    data = event.get("data")
    if isinstance(data, Mapping):
        data_issue = data.get("issue")
        if isinstance(data_issue, Mapping):
            sources.append(data_issue)
        sources.append(data)

    sources.append(event)
    return sources


def _is_status_change_event(
    event: Mapping[str, Any], sources: Sequence[Mapping[str, Any]]
) -> bool:
    event_names = {
        _normalize_compact(source.get(key))
        for source in sources
        for key in _EVENT_KEYS
        if source.get(key) is not None
    }

    if any(name in {"statuschanged", "statuschange"} for name in event_names):
        return True

    has_update_event = any(name in {"update", "updated", "issueupdated", "updatedissue"} for name in event_names)
    if has_update_event and _has_status_change_metadata(event, sources):
        return True

    # Some webhook payloads omit an explicit event name but still provide change
    # metadata. Treat those as status changes only when the changed field is clear.
    return not event_names and _has_status_change_metadata(event, sources)


def _has_status_change_metadata(
    event: Mapping[str, Any], sources: Sequence[Mapping[str, Any]]
) -> bool:
    for source in sources:
        for key in _UPDATED_FIELD_KEYS:
            if _contains_status_field(source.get(key)):
                return True

    changes = event.get("changes")
    if _contains_status_field(changes):
        return True

    if isinstance(changes, Mapping):
        return any(_is_status_field(field) for field in changes)

    if _is_sequence(changes):
        return any(_change_record_is_status_related(change) for change in changes)

    return False


def _status_from_event(
    event: Mapping[str, Any], sources: Sequence[Mapping[str, Any]]
) -> Any:
    for source in sources:
        for key in _NEW_STATUS_KEYS:
            status = _status_value(source.get(key))
            if status:
                return status

    changed_status = _status_from_changes(event.get("changes"))
    if changed_status:
        return changed_status

    for source in sources:
        for key in ("status", "state", "workflowState", "workflow_state"):
            status = _status_value(source.get(key))
            if status:
                return status

    return None


def _status_from_changes(changes: Any) -> str | None:
    if isinstance(changes, Mapping):
        for field, change in changes.items():
            if _is_status_field(field):
                status = _new_value_from_change(change)
                if status:
                    return status

    if _is_sequence(changes):
        for change in changes:
            if not _change_record_is_status_related(change):
                continue
            status = _new_value_from_change(change)
            if status:
                return status

    return None


def _new_value_from_change(change: Any) -> str | None:
    change_value = _status_value(change)
    if isinstance(change, Mapping):
        for key in ("to", "new", "after", "newValue", "new_value", "value"):
            status = _status_value(change.get(key))
            if status:
                return status

    return change_value


def _change_record_is_status_related(change: Any) -> bool:
    if not isinstance(change, Mapping):
        return False

    for key in ("field", "fieldName", "field_name", "name", "property"):
        if _is_status_field(change.get(key)):
            return True

    return any(_is_status_field(key) for key in change)


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(_is_status_field(field) for field in value)

    if _is_sequence(value):
        for item in value:
            if isinstance(item, Mapping):
                if _change_record_is_status_related(item):
                    return True
            elif _is_status_field(item):
                return True

    return _is_status_field(value)


def _is_status_field(value: Any) -> bool:
    normalized = _normalize_compact(value)
    if not normalized:
        return False
    return normalized in _STATUS_FIELD_NAMES or normalized.endswith("status")


def _first_text(sources: Sequence[Mapping[str, Any]], keys: Sequence[str]) -> str | None:
    for source in sources:
        for key in keys:
            value = source.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _status_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("name", "label", "title", "value"):
            status = _status_value(value.get(key))
            if status:
                return status
        return None

    if isinstance(value, str) and value.strip():
        return value

    return None


def _has_research_prefix(title: str) -> bool:
    return re.match(r"^\s*cursor\s+researching\b", title, re.IGNORECASE) is not None


def _normalize_words(value: Any) -> str:
    if value is None:
        return ""

    text = str(value).strip()
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def _normalize_compact(value: Any) -> str:
    return _normalize_words(value).replace(" ", "")


def _is_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    print(json.dumps(update))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
