"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_DIRECT_STATUS_CHANGE = {
    "status changed",
    "status change",
    "status updated",
    "state changed",
    "state change",
    "state updated",
    "workflow state changed",
    "workflow state change",
    "workflow state updated",
}
_GENERIC_ISSUE_UPDATE = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}
_TRIGGER_KEYS = ("trigger", "webhookType", "action", "type", "event", "webhookAction")
_ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "key", "id")
_TITLE_KEYS = ("title",)
_EXPLICIT_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "toStatus",
    "to_status",
    "statusName",
    "status_name",
    "stateName",
    "state_name",
    "workflowStateName",
    "workflow_state_name",
)
_CURRENT_STATUS_KEYS = ("status", "state", "workflowState", "workflow_state")
_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflowstate",
    "workflow state",
    "workflow_state",
    "statusid",
    "stateid",
    "workflowstateid",
    "workflow state id",
    "workflow_state_id",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title-update action when a Linear issue moves to to research.

    The handler accepts Cursor automation payloads, which commonly wrap the
    Linear payload under ``triggerContext``, and direct Linear issue webhook
    shapes where issue data is under ``data`` or ``data.issue``.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _candidate_contexts(event)
    if not _is_status_change_event(contexts):
        return None

    if not any(_is_target_status(status) for status in _status_candidates(contexts)):
        return None

    issue_id = _first_text(contexts, _ISSUE_ID_KEYS)
    title = _first_text(contexts, _TITLE_KEYS)
    if not issue_id or not title:
        return None

    cleaned_title = title.strip()
    if not cleaned_title or _has_prefix(cleaned_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {cleaned_title}",
    }


def _candidate_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)

    automation_info = event.get("automation_trigger_info")
    if isinstance(automation_info, Mapping):
        add(automation_info.get("triggerContext"))

    add(event.get("triggerContext"))
    add(event)

    data = event.get("data")
    add(data)
    if isinstance(data, Mapping):
        add(data.get("issue"))
        add(data.get("node"))

    add(event.get("issue"))
    add(event.get("node"))

    return contexts


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    saw_generic_update = False

    for context in contexts:
        for key in _TRIGGER_KEYS:
            normalized = _normalize_text(context.get(key))
            if not normalized:
                continue
            if normalized in _DIRECT_STATUS_CHANGE:
                return True
            if normalized in _GENERIC_ISSUE_UPDATE:
                saw_generic_update = True

    return saw_generic_update and _has_status_change_evidence(contexts)


def _has_status_change_evidence(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        if any(_has_key(context, key) for key in _EXPLICIT_STATUS_KEYS):
            return True

        if _changed_fields_include_status(context.get("updatedFields")):
            return True

        for change_container_key in ("changes", "updatedFrom", "updated_from"):
            changes = context.get(change_container_key)
            if isinstance(changes, Mapping) and any(
                _is_status_field(field_name) for field_name in changes
            ):
                return True

    return False


def _status_candidates(contexts: list[Mapping[str, Any]]) -> list[str]:
    candidates: list[str] = []

    for context in contexts:
        for key in _EXPLICIT_STATUS_KEYS:
            candidates.extend(_status_value(context.get(key)))

        for change_container_key in ("changes",):
            changes = context.get(change_container_key)
            if isinstance(changes, Mapping):
                for field_name, change in changes.items():
                    if _is_status_field(field_name):
                        candidates.extend(_new_status_from_change(change))

        for key in _CURRENT_STATUS_KEYS:
            candidates.extend(_status_value(context.get(key)))

    return [candidate for candidate in candidates if candidate]


def _new_status_from_change(change: Any) -> list[str]:
    if not isinstance(change, Mapping):
        return _status_value(change)

    candidates: list[str] = []
    for key in ("new", "newValue", "new_value", "to", "toValue", "to_value", "after", "current"):
        candidates.extend(_status_value(change.get(key)))
    return candidates


def _status_value(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, Mapping):
        candidates: list[str] = []
        for key in ("name", "title", "status", "state", "workflowState", "workflow_state"):
            candidates.extend(_status_value(value.get(key)))
        return candidates
    return [str(value)]


def _first_text(contexts: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _changed_fields_include_status(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)
    if isinstance(value, Mapping):
        return any(_is_status_field(key) for key in value)
    if isinstance(value, list | tuple | set):
        return any(_is_status_field(item) for item in value)
    return False


def _is_status_field(value: Any) -> bool:
    normalized = _normalize_text(value)
    compact = normalized.replace(" ", "")
    return normalized in _STATUS_FIELD_NAMES or compact in _STATUS_FIELD_NAMES


def _has_key(context: Mapping[str, Any], target_key: str) -> bool:
    return any(key == target_key for key in context)


def _is_target_status(value: str) -> bool:
    return _normalize_text(value) == TARGET_STATUS


def _has_prefix(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.casefold().split())


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
