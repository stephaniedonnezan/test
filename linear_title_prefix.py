"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import re
from collections.abc import Iterator, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_CHANGE_TRIGGER = "status changed"

_TRIGGER_KEYS = ("trigger", "webhookType", "webhook_type", "action", "type")
_STATUS_KEYS = ("newStatus", "new_status", "newState", "new_state", "status")
_ID_KEYS = ("id", "issueId", "issue_id", "identifier")
_TITLE_KEYS = ("title", "name")
_CAMEL_CASE_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_WORD_SEPARATOR = re.compile(r"[\W_]+")


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update action for issues moved to research.

    The automation payload may include issue fields at the top level, in
    ``triggerContext``, or nested under Linear-style ``data.issue`` objects.
    """

    if not isinstance(event, Mapping):
        return None

    issue = _merged_issue_fields(event)
    if not _is_status_change(issue):
        return None
    if _normalise_text(_first_value(issue, _STATUS_KEYS) or _state_name(issue)) != TARGET_STATUS:
        return None

    issue_id = _string_value(_first_value(issue, _ID_KEYS))
    title = _string_value(_first_value(issue, _TITLE_KEYS))
    if not issue_id or not title:
        return None

    title = title.strip()
    if not title or _normalise_text(title).startswith(PREFIX.casefold()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _merged_issue_fields(event: Mapping[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for container in _candidate_containers(event):
        merged.update(container)
    return merged


def _candidate_containers(event: Mapping[str, Any]) -> Iterator[Mapping[str, Any]]:
    """Yield nested payload maps from broad to specific.

    Later maps override earlier ones so outer automation metadata such as
    ``newStatus`` wins over nested Linear issue state fields.
    """

    trigger_context = _mapping_at(event, "triggerContext")
    data = _mapping_at(event, "data")
    trigger_data = _mapping_at(trigger_context, "data") if trigger_context else None

    for container in (trigger_data, data):
        issue = _mapping_at(container, "issue") if container else None
        if issue:
            yield issue
        if container:
            yield container

    for container in (trigger_context, event):
        issue = _mapping_at(container, "issue") if container else None
        if issue:
            yield issue
        if container:
            yield container


def _mapping_at(container: Mapping[str, Any] | None, key: str) -> Mapping[str, Any] | None:
    if not isinstance(container, Mapping):
        return None
    value = container.get(key)
    return value if isinstance(value, Mapping) else None


def _is_status_change(issue: Mapping[str, Any]) -> bool:
    return any(
        _normalise_text(value) == STATUS_CHANGE_TRIGGER
        for key in _TRIGGER_KEYS
        if (value := issue.get(key)) is not None
    )


def _state_name(issue: Mapping[str, Any]) -> Any:
    state = issue.get("state")
    if isinstance(state, Mapping):
        return state.get("name")
    return None


def _first_value(container: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in container:
            return container[key]
    return None


def _string_value(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalise_text(value: Any) -> str:
    value = _CAMEL_CASE_BOUNDARY.sub(" ", str(value))
    value = _WORD_SEPARATOR.sub(" ", value)
    return " ".join(value.casefold().split())
