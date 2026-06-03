"""Build Linear issue title updates for research status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping, Sequence
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_CHANGED_TRIGGERS = {
    "status change",
    "status changed",
    "status updated",
    "state change",
    "state changed",
    "workflow state change",
    "workflow state changed",
}
_ISSUE_UPDATED_TRIGGERS = {
    "issue update",
    "issue updated",
    "update",
    "updated",
    "updated issue",
}
_STATUS_FIELD_NAMES = {
    "state",
    "stateid",
    "status",
    "statusid",
    "workflowstate",
    "workflowstateid",
    "workflow_state",
    "workflow_state_id",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to research."""

    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_change_event(contexts):
        return None

    status = _new_status(contexts)
    if _normalize_words(status) != TARGET_STATUS:
        return None

    issue_id = _first_string(
        contexts,
        (
            "identifier",
            "issueIdentifier",
            "issue_identifier",
            "issueId",
            "issue_id",
            "id",
        ),
    )
    title = _first_string(contexts, ("title", "name"))
    if not issue_id or not title:
        return None

    clean_title = title.strip()
    if not clean_title or _has_title_prefix(clean_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {clean_title}",
    }


def _contexts(event: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    """Return likely Linear payload objects from most to least issue-specific."""

    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        add(trigger_context.get("issue"))
        trigger_data = trigger_context.get("data")
        if isinstance(trigger_data, Mapping):
            add(trigger_data.get("issue"))
            add(trigger_data)
        add(trigger_context)

    data = event.get("data")
    if isinstance(data, Mapping):
        add(data.get("issue"))
        add(data)

    add(event.get("issue"))
    add(event)
    return tuple(contexts)


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    context_list = tuple(contexts)
    trigger_values = {
        _normalize_words(value)
        for context in context_list
        for key in ("trigger", "webhookType", "action", "type")
        for value in _string_values(context.get(key))
    }

    if trigger_values & _STATUS_CHANGED_TRIGGERS:
        return True

    if not trigger_values & _ISSUE_UPDATED_TRIGGERS:
        return False

    return any(_updated_status_field(context) for context in context_list)


def _updated_status_field(context: Mapping[str, Any]) -> bool:
    for key in (
        "updatedFields",
        "updated_fields",
        "changedFields",
        "changed_fields",
        "updatedField",
        "updated_field",
    ):
        for value in _string_values(context.get(key)):
            if _normalize_field_name(value) in _STATUS_FIELD_NAMES:
                return True

    for key in ("changes", "updatedFrom", "updated_from"):
        value = context.get(key)
        if isinstance(value, Mapping):
            for field_name in value:
                if _normalize_field_name(str(field_name)) in _STATUS_FIELD_NAMES:
                    return True

    return False


def _new_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    context_list = tuple(contexts)
    for key in ("newStatus", "new_status", "newState", "new_state"):
        value = _first_string(context_list, (key,))
        if value:
            return value

    for context in context_list:
        for key in ("status", "state", "workflowState", "workflow_state"):
            value = _status_name(context.get(key))
            if value:
                return value

    for context in context_list:
        for key in ("changes",):
            value = _status_name(_status_from_change_container(context.get(key)))
            if value:
                return value

    return None


def _status_from_change_container(value: Any) -> Any:
    if not isinstance(value, Mapping):
        return None

    for field_name, change in value.items():
        if _normalize_field_name(str(field_name)) not in _STATUS_FIELD_NAMES:
            continue
        if isinstance(change, Mapping):
            for key in ("to", "new", "after", "current"):
                if key in change:
                    return change[key]
        return change

    return None


def _status_name(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        return _first_string((value,), ("name", "title", "status"))
    return None


def _first_string(
    contexts: Iterable[Mapping[str, Any]], keys: Sequence[str]
) -> str | None:
    normalized_keys = tuple(_normalize_field_name(key) for key in keys)

    for context in contexts:
        normalized_context = {
            _normalize_field_name(str(key)): value for key, value in context.items()
        }
        for normalized_key in normalized_keys:
            value = normalized_context.get(normalized_key)
            if isinstance(value, str) and value.strip():
                return value

    return None


def _string_values(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, Mapping):
        return [item for item in value.values() if isinstance(item, str)]
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [item for item in value if isinstance(item, str)]
    return []


def _normalize_words(value: str | None) -> str:
    if not value:
        return ""

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    words = re.sub(r"[^A-Za-z0-9]+", " ", spaced).strip().casefold()
    return re.sub(r"\s+", " ", words)


def _normalize_field_name(value: str) -> str:
    return _normalize_words(value).replace(" ", "")


def _has_title_prefix(title: str) -> bool:
    normalized_title = title.casefold()
    normalized_prefix = TITLE_PREFIX.casefold()
    return normalized_title == normalized_prefix or normalized_title.startswith(
        f"{normalized_prefix}:"
    )


def main() -> int:
    """Read an event JSON document from stdin and print the action as JSON."""

    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
