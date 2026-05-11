"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections import deque
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_CHANGE_EVENTS = {"status changed", "status change"}
_ISSUE_UPDATE_EVENTS = {"issue updated", "updated issue", "update", "updated"}
_STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflowstateid"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to research."""
    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    status = _find_status(event)
    if _normalize_words(status) != TARGET_STATUS:
        return None

    issue_id = _find_issue_id(event)
    title = _extract_text(_find_value(event, ("title",)))
    if not issue_id or not title:
        return None

    title = title.strip()
    if not title or _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    event_names = {
        _normalize_words(value)
        for value in _find_values(event, ("trigger", "webhookType", "action", "type"))
    }

    if event_names & _STATUS_CHANGE_EVENTS:
        return True

    if event_names & _ISSUE_UPDATE_EVENTS and _updated_fields_include_status(event):
        return True

    return False


def _updated_fields_include_status(event: Mapping[str, Any]) -> bool:
    for fields in _find_values(
        event,
        ("updatedFields", "updated_fields", "changedFields", "changed_fields"),
    ):
        if _contains_status_field_name(fields):
            return True
    return False


def _contains_status_field_name(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_identifier(value) in _STATUS_FIELD_NAMES

    if isinstance(value, Mapping):
        return any(
            _contains_status_field_name(key) or _contains_status_field_name(item)
            for key, item in value.items()
        )

    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        return any(_contains_status_field_name(item) for item in value)

    return False


def _find_status(event: Mapping[str, Any]) -> str | None:
    explicit_status = _find_value(
        event,
        ("newStatus", "new_status", "newState", "new_state", "toStatus", "to_status"),
    )
    if explicit_status is not None:
        return _extract_text(explicit_status)

    status = _find_value(event, ("status", "state", "workflowState", "workflow_state"))
    return _extract_text(status)


def _find_issue_id(event: Mapping[str, Any]) -> str | None:
    issue_id = _extract_text(_find_value(event, ("issueId", "issue_id", "identifier")))
    if issue_id:
        return issue_id

    for mapping in _iter_mappings(event):
        if _find_value_in_mapping(mapping, ("title",)) is None:
            continue
        issue_id = _extract_text(_find_value_in_mapping(mapping, ("id",)))
        if issue_id:
            return issue_id

    return None


def _find_value(event: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    for mapping in _iter_mappings(event):
        value = _find_value_in_mapping(mapping, keys)
        if value is not None:
            return value
    return None


def _find_values(event: Mapping[str, Any], keys: tuple[str, ...]) -> list[Any]:
    values: list[Any] = []
    for mapping in _iter_mappings(event):
        value = _find_value_in_mapping(mapping, keys)
        if value is not None:
            values.append(value)
    return values


def _find_value_in_mapping(mapping: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    normalized_keys = {_normalize_identifier(key) for key in keys}
    for key, value in mapping.items():
        if _normalize_identifier(str(key)) in normalized_keys:
            return value
    return None


def _iter_mappings(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    queue: deque[Any] = deque([event])
    while queue:
        current = queue.popleft()
        if isinstance(current, Mapping):
            yield current
            queue.extend(current.values())
        elif isinstance(current, list):
            queue.extend(current)


def _extract_text(value: Any) -> str | None:
    if value is None:
        return None

    if isinstance(value, str):
        return value.strip()

    if isinstance(value, (int, float)):
        return str(value)

    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            text = _extract_text(value.get(key))
            if text:
                return text

    return None


def _normalize_words(value: Any) -> str:
    text = _extract_text(value)
    if not text:
        return ""

    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def _normalize_identifier(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _has_research_prefix(title: str) -> bool:
    return re.match(r"^\s*cursor\s+researching\b", title, re.IGNORECASE) is not None


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
