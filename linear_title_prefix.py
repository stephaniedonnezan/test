"""Build title update actions for Linear issues moved to research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_TRIGGER_KEYS = ("trigger", "webhookType", "action", "type", "event")
_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "newWorkflowState",
    "new_workflow_state",
    "status",
    "state",
    "workflowState",
    "workflow_state",
)
_EXPLICIT_NEW_STATUS_KEYS = _STATUS_KEYS[:6]
_TITLE_KEYS = ("title", "name")
_ID_KEYS = ("issueId", "issue_id", "id", "identifier", "key")
_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflow state",
    "workflowstate",
    "state id",
    "stateid",
    "workflow state id",
    "workflowstateid",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return an issue title update action when a Linear issue enters research."""
    if not isinstance(event, Mapping):
        return None

    contexts = _event_contexts(event)
    status = _extract_new_status(contexts)
    if _normalize(status) != TARGET_STATUS:
        return None

    if not _is_status_change_event(contexts):
        return None

    title = _extract_string(contexts, _TITLE_KEYS)
    issue_id = _extract_string(contexts, _ID_KEYS)
    if not title or not issue_id or _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _event_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)

    add(event.get("triggerContext"))
    add(event)
    data = event.get("data")
    add(data)
    if isinstance(data, Mapping):
        add(data.get("issue"))
        add(data.get("object"))
    add(event.get("issue"))
    add(event.get("object"))
    return contexts


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    saw_generic_update = False

    for context in contexts:
        for key in _TRIGGER_KEYS:
            normalized = _normalize(context.get(key))
            compact = normalized.replace(" ", "")
            if compact in {
                "statuschanged",
                "statuschange",
                "statechanged",
                "statechange",
                "workflowstatechanged",
                "workflowstatechange",
            }:
                return True
            if normalized in {"update", "updated", "issue updated", "updated issue"}:
                saw_generic_update = True

    return saw_generic_update and _updated_fields_include_status(contexts)


def _updated_fields_include_status(contexts: Iterable[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            if _field_collection_mentions_status(context.get(key)):
                return True

        changes = context.get("changes")
        if isinstance(changes, Mapping):
            if any(_is_status_field(key) for key in changes):
                return True
            if _field_collection_mentions_status(changes.get("fields")):
                return True

    return False


def _field_collection_mentions_status(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)
    if isinstance(value, Mapping):
        return any(_is_status_field(key) or _field_collection_mentions_status(item) for key, item in value.items())
    if isinstance(value, Iterable):
        return any(_field_collection_mentions_status(item) for item in value)
    return False


def _is_status_field(value: Any) -> bool:
    return _normalize(value) in _STATUS_FIELD_NAMES


def _extract_new_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    contexts = list(contexts)

    for key in _EXPLICIT_NEW_STATUS_KEYS:
        status = _extract_status_by_key(contexts, key)
        if status:
            return status

    status_from_changes = _extract_status_from_changes(contexts)
    if status_from_changes:
        return status_from_changes

    for key in _STATUS_KEYS[6:]:
        status = _extract_status_by_key(contexts, key)
        if status:
            return status

    return None


def _extract_status_by_key(contexts: Iterable[Mapping[str, Any]], key: str) -> str | None:
    for context in contexts:
        if key in context:
            value = _status_value(context[key])
            if value:
                return value
    return None


def _extract_status_from_changes(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        changes = context.get("changes")
        if not isinstance(changes, Mapping):
            continue

        for key, value in changes.items():
            if not _is_status_field(key):
                continue
            changed_to = _changed_to_value(value)
            if changed_to:
                return changed_to

    return None


def _changed_to_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("to", "after", "new", "newValue", "new_value", "current"):
            if key in value:
                extracted = _status_value(value[key])
                if extracted:
                    return extracted
    return _status_value(value)


def _status_value(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, Mapping):
        for key in ("name", "title", "status", "state"):
            if key in value:
                nested = _status_value(value[key])
                if nested:
                    return nested
    return None


def _extract_string(contexts: Iterable[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        for context in contexts:
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _normalize(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    spaced = re.sub(r"[^A-Za-z0-9]+", " ", spaced)
    return re.sub(r"\s+", " ", spaced).strip().lower()


def _has_research_prefix(title: str) -> bool:
    return title.strip().lower().startswith(PREFIX.lower())


def main() -> int:
    event = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(event)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
