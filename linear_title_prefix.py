"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflow state",
    "workflow status",
    "status id",
    "state id",
    "workflow state id",
}
_STATUS_CHANGE_EVENT_NAMES = {
    "status changed",
    "status change",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
}
_UPDATE_EVENT_NAMES = {
    "update",
    "updated",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return an issue title update action when a Linear issue enters research.

    The handler accepts the flat Cursor automation trigger context as well as
    common nested Linear webhook shapes. It returns None when the event is not a
    status transition to "to research" or when the title is already prefixed.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    if not _is_target_status(_new_status(event)):
        return None

    issue_id = _issue_id(event)
    title = _issue_title(event)
    if not issue_id or not title:
        return None

    stripped_title = title.strip()
    if stripped_title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {stripped_title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    for key in ("trigger", "webhookType"):
        for value in _values_for_key(event, key, max_depth=2):
            if _normalized(value) in _STATUS_CHANGE_EVENT_NAMES:
                return True

    event_names = [
        _normalized(value)
        for key in ("trigger", "webhookType", "action", "type")
        for value in _values_for_key(event, key, max_depth=2)
    ]
    if any(name in _UPDATE_EVENT_NAMES for name in event_names):
        return _updated_status_fields(event)

    return False


def _updated_status_fields(event: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        for value in _values_for_key(event, key, max_depth=3):
            if _contains_status_field(value):
                return True
    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalized(value) in _STATUS_FIELD_NAMES

    if isinstance(value, Mapping):
        return any(_contains_status_field(key) for key in value.keys())

    if isinstance(value, Iterable):
        return any(_contains_status_field(item) for item in value)

    return False


def _new_status(event: Mapping[str, Any]) -> str | None:
    explicit_keys = (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "toStatus",
        "to_status",
        "toState",
        "to_state",
    )
    for candidate in _status_candidates(event):
        for key in explicit_keys:
            value = _string(candidate.get(key))
            if value:
                return value

    for candidate in _issue_candidates(event):
        for key in ("status", "state", "workflowState", "workflow_state"):
            value = _name_or_string(candidate.get(key))
            if value:
                return value

    return None


def _status_candidates(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    candidates: list[Mapping[str, Any]] = [event]

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        candidates.append(trigger_context)

    data = event.get("data")
    if isinstance(data, Mapping):
        candidates.append(data)
        data_issue = data.get("issue")
        if isinstance(data_issue, Mapping):
            candidates.append(data_issue)

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        candidates.append(issue)

    return candidates


def _issue_title(event: Mapping[str, Any]) -> str | None:
    for candidate in _issue_candidates(event):
        value = _string(candidate.get("title"))
        if value:
            return value
    return None


def _issue_id(event: Mapping[str, Any]) -> str | None:
    for candidate in _issue_candidates(event):
        for key in ("issueId", "issue_id", "identifier", "id"):
            value = _string(candidate.get(key))
            if value:
                return value
    return None


def _issue_candidates(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    candidates: list[Mapping[str, Any]] = []

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        candidates.append(trigger_context)

    data = event.get("data")
    if isinstance(data, Mapping):
        data_issue = data.get("issue")
        if isinstance(data_issue, Mapping):
            candidates.append(data_issue)
        candidates.append(data)

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        candidates.append(issue)

    candidates.append(event)
    return candidates


def _values_for_key(value: Any, target_key: str, max_depth: int) -> Iterable[Any]:
    if max_depth < 0 or not isinstance(value, Mapping):
        return

    if target_key in value:
        yield value[target_key]

    for nested in value.values():
        if isinstance(nested, Mapping):
            yield from _values_for_key(nested, target_key, max_depth - 1)


def _name_or_string(value: Any) -> str | None:
    if isinstance(value, Mapping):
        return _string(value.get("name"))
    return _string(value)


def _string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    stripped = value.strip()
    return stripped or None


def _is_target_status(value: str | None) -> bool:
    return _normalized(value) == TARGET_STATUS


def _normalized(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value.strip())
    normalized = re.sub(r"[^A-Za-z0-9]+", " ", spaced).lower()
    return " ".join(normalized.split())


def _main() -> int:
    payload = json.load(sys.stdin)
    update = build_issue_title_update(payload)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
