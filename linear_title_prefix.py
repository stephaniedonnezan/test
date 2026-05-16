"""Build Linear issue title updates for Cursor research automation."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_DIRECT_STATUS_CHANGE_SIGNALS = {
    "status change",
    "status changed",
    "statuschanged",
    "state change",
    "state changed",
    "workflow state change",
    "workflow state changed",
}
_ISSUE_UPDATE_SIGNALS = {
    "issue update",
    "issue updated",
    "updated issue",
    "update",
    "updated",
}
_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflowstate",
    "workflow state",
    "statusid",
    "status id",
    "stateid",
    "state id",
    "workflowstateid",
    "workflow state id",
}
_EXPLICIT_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "toStatus",
    "to_status",
    "statusName",
    "status_name",
    "stateName",
    "state_name",
    "workflowStateName",
    "workflow_state_name",
)
_STATUS_CONTAINER_KEYS = ("state", "workflowState", "workflow_state", "status")
_ISSUE_ID_KEYS = ("issueId", "issue_id", "id", "identifier")
_TRIGGER_KEYS = ("trigger", "webhookType", "webhook_type", "action", "type", "eventType", "event_type")


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to to research.

    The function is intentionally side-effect free so the automation runtime can
    decide how to apply the returned action.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    if _normalized_status(_status_from_event(event)) != TARGET_STATUS:
        return None

    issue = _issue_identity(event)
    if issue is None:
        return None

    issue_id, title = issue
    if title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _issue_identity(event: Mapping[str, Any]) -> tuple[str, str] | None:
    for candidate in _issue_candidates(event):
        issue_id = _first_text(candidate, _ISSUE_ID_KEYS)
        title = _text_value(candidate.get("title"))
        if issue_id and title:
            return issue_id, title
    return None


def _issue_candidates(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    candidates: list[Mapping[str, Any]] = []
    trigger_context = event.get("triggerContext")
    data = event.get("data")
    issue = event.get("issue")

    if isinstance(trigger_context, Mapping):
        candidates.append(trigger_context)

    if isinstance(data, Mapping):
        data_issue = data.get("issue")
        if isinstance(data_issue, Mapping):
            candidates.append(data_issue)

    if isinstance(issue, Mapping):
        candidates.append(issue)

    if isinstance(data, Mapping):
        candidates.append(data)

    candidates.append(event)
    return candidates


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    trigger_values = {_normalized_signal(value) for value in _trigger_values(event)}
    if trigger_values & _DIRECT_STATUS_CHANGE_SIGNALS:
        return True

    if trigger_values & _ISSUE_UPDATE_SIGNALS and _updated_fields_include_status(event):
        return True

    return _updated_fields_include_status(event) and not trigger_values


def _trigger_values(value: Any) -> Iterable[Any]:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if key in _TRIGGER_KEYS:
                yield child
            yield from _trigger_values(child)
    elif isinstance(value, list):
        for item in value:
            yield from _trigger_values(item)


def _updated_fields_include_status(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized_key = _normalized_signal(key)
            if normalized_key in {"updatedfields", "updated fields", "changedfields", "changed fields"}:
                if _field_collection_includes_status(child):
                    return True
            if normalized_key in {"updatedfrom", "updated from", "changes", "changed"}:
                if _change_mapping_includes_status(child):
                    return True
            if _updated_fields_include_status(child):
                return True
    elif isinstance(value, list):
        return any(_updated_fields_include_status(item) for item in value)
    return False


def _field_collection_includes_status(value: Any) -> bool:
    if isinstance(value, str):
        return _normalized_signal(value) in _STATUS_FIELD_NAMES
    if isinstance(value, Mapping):
        return _change_mapping_includes_status(value)
    if isinstance(value, Iterable):
        return any(_field_collection_includes_status(item) for item in value)
    return False


def _change_mapping_includes_status(value: Any) -> bool:
    if not isinstance(value, Mapping):
        return False

    return any(_normalized_signal(key) in _STATUS_FIELD_NAMES for key in value)


def _status_from_event(event: Mapping[str, Any]) -> str | None:
    containers = _status_candidates(event)

    for container in containers:
        status = _first_text(container, _EXPLICIT_STATUS_KEYS)
        if status:
            return status

    for container in containers:
        for key in _STATUS_CONTAINER_KEYS:
            status = _status_text(container.get(key))
            if status:
                return status

    return None


def _status_candidates(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    candidates: list[Mapping[str, Any]] = []
    trigger_context = event.get("triggerContext")

    if isinstance(trigger_context, Mapping):
        candidates.append(trigger_context)

    candidates.append(event)

    for candidate in _issue_candidates(event):
        if candidate not in candidates:
            candidates.append(candidate)

    return candidates


def _status_text(value: Any) -> str | None:
    text = _text_value(value)
    if text:
        return text

    if isinstance(value, Mapping):
        return _first_text(value, ("name", "title", "label"))

    return None


def _first_text(container: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for key in keys:
        text = _text_value(container.get(key))
        if text:
            return text
    return None


def _text_value(value: Any) -> str | None:
    if isinstance(value, str):
        text = value.strip()
        return text or None
    return None


def _normalized_status(value: str | None) -> str:
    return _normalized_words(value)


def _normalized_signal(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return _normalized_words(value).replace("status changed", "statuschanged")


def _normalized_words(value: str | None) -> str:
    if value is None:
        return ""

    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value.strip())
    words = re.sub(r"[^A-Za-z0-9]+", " ", separated).lower().split()
    return " ".join(words)


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
