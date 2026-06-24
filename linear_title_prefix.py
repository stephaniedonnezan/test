"""Build title update actions for Linear issues moved to research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {
    "status",
    "status name",
    "state",
    "state name",
    "state id",
    "workflow state",
    "workflow state name",
    "workflow state id",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue enters research.

    The Cursor automation payload is flat under ``triggerContext``, while native
    Linear webhooks commonly place issue data under ``data`` or ``data.issue``.
    This function accepts those shapes and returns a serializable action that an
    automation runner can use to update the Linear issue title.
    """

    if not isinstance(event, Mapping):
        return None

    sources = _payload_sources(event)
    issue_id = _extract_issue_id(sources)
    title = _extract_title(sources)

    if not issue_id or not title:
        return None
    if title.lower().startswith(PREFIX.lower()):
        return None
    if not _is_status_change(event, sources):
        return None

    new_status = _extract_new_status(sources)
    if _normalize_words(new_status) != TARGET_STATUS:
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _payload_sources(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return likely issue/metadata mappings, with issue-specific data first."""

    trigger_context = _mapping_at(event, "triggerContext")
    data = _mapping_at(event, "data")
    direct_issue = _mapping_at(event, "issue")
    data_issue = _mapping_at(data, "issue") if data else None
    node = _mapping_at(event, "node")

    sources: list[Mapping[str, Any]] = []
    for candidate in (data_issue, direct_issue, data, trigger_context, node, event):
        if candidate and candidate not in sources:
            sources.append(candidate)
    return sources


def _mapping_at(source: Mapping[str, Any] | None, key: str) -> Mapping[str, Any] | None:
    value = source.get(key) if isinstance(source, Mapping) else None
    return value if isinstance(value, Mapping) else None


def _extract_issue_id(sources: Sequence[Mapping[str, Any]]) -> str | None:
    for source in sources:
        for key in ("identifier", "key", "issueId", "issue_id", "id"):
            value = _clean_string(source.get(key))
            if value:
                return value
    return None


def _extract_title(sources: Sequence[Mapping[str, Any]]) -> str | None:
    for source in sources:
        for key in ("title", "issueTitle", "name"):
            value = _clean_string(source.get(key))
            if value:
                return value
    return None


def _is_status_change(
    event: Mapping[str, Any], sources: Sequence[Mapping[str, Any]]
) -> bool:
    event_names = _event_names(sources)
    if any(name in {"status changed", "status change", "state changed"} for name in event_names):
        return True
    if "workflow state changed" in event_names:
        return True

    update_event = bool(
        event_names
        & {
            "update",
            "updated",
            "issue update",
            "issue updated",
            "updated issue",
        }
    )
    issue_event = bool(event_names & {"issue", "issue update", "issue updated", "updated issue"})

    if (update_event or issue_event) and _has_status_change_marker(event, sources):
        return True

    return False


def _event_names(sources: Sequence[Mapping[str, Any]]) -> set[str]:
    names: set[str] = set()
    for source in sources:
        for key in ("trigger", "webhookType", "action", "type", "event", "eventType"):
            normalized = _normalize_words(source.get(key))
            if normalized:
                names.add(normalized)
    return names


def _has_status_change_marker(
    event: Mapping[str, Any], sources: Sequence[Mapping[str, Any]]
) -> bool:
    for source in (*sources, event):
        for key in ("updatedFields", "changedFields", "changes", "updatedFrom"):
            value = source.get(key)
            if _contains_status_field(value):
                return True
    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(_is_status_field(key) for key in value.keys())
    if isinstance(value, str):
        return _is_status_field(value)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return any(_contains_status_field(item) for item in value)
    return False


def _is_status_field(value: Any) -> bool:
    normalized = _normalize_words(value)
    return normalized in _STATUS_FIELD_NAMES


def _extract_new_status(sources: Sequence[Mapping[str, Any]]) -> str | None:
    direct_keys = (
        "newStatus",
        "new_status",
        "statusName",
        "stateName",
        "workflowStateName",
    )

    for source in sources:
        for key in direct_keys:
            value = _clean_string(source.get(key))
            if value:
                return value

    status_from_changes = _extract_status_from_changes(sources)
    if status_from_changes:
        return status_from_changes

    for source in sources:
        for key in ("status", "state", "workflowState"):
            value = _status_value(source.get(key))
            if value:
                return value

    return None


def _extract_status_from_changes(sources: Sequence[Mapping[str, Any]]) -> str | None:
    for source in sources:
        changes = source.get("changes")
        if isinstance(changes, Mapping):
            for key, value in changes.items():
                if not _is_status_field(key):
                    continue
                changed_value = _status_value(value)
                if changed_value:
                    return changed_value

    return None


def _status_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("newValue", "new_value", "to", "after", "value", "name"):
            nested = _status_value(value.get(key))
            if nested:
                return nested
        return None
    return _clean_string(value)


def _clean_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def _normalize_words(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    with_word_boundaries = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    with_word_boundaries = re.sub(
        r"([A-Z]+)([A-Z][a-z])", r"\1 \2", with_word_boundaries
    )
    words = re.findall(r"[A-Za-z0-9]+", with_word_boundaries)
    return " ".join(word.lower() for word in words)


def main() -> int:
    payload = json.load(sys.stdin)
    result = build_issue_title_update(payload)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
