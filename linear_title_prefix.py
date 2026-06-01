"""Build Linear issue title updates for research-status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"

_EXPLICIT_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newStatusName",
    "statusName",
    "stateName",
    "workflowStateName",
)
_STATUS_KEYS = ("status", "state", "workflowState", "workflow_state")
_TRIGGER_KEYS = ("trigger", "webhookType", "webhook_type", "action", "type")
_STATUS_FIELD_NAMES = {
    "status",
    "statusid",
    "statusname",
    "state",
    "stateid",
    "statename",
    "workflowstate",
    "workflowstateid",
    "workflowstatename",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action for Linear issues moved to To Research.

    The automation runner can pass either a flat trigger context or a nested
    Linear webhook payload. Returning ``None`` means no title update is needed.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _collect_contexts(event)
    if not _is_status_change_event(contexts):
        return None

    new_status = _find_new_status(contexts)
    if _normalize_words(new_status) != TARGET_STATUS:
        return None

    issue_id = _find_first_text(contexts, ("issueId", "issue_id", "identifier"))
    if issue_id is None:
        issue_id = _find_first_text(contexts, ("id",))

    title = _find_first_text(contexts, ("title",))
    if issue_id is None or title is None:
        return None

    if title.casefold().startswith(TITLE_PREFIX.casefold()):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _collect_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and not any(value is existing for existing in contexts):
            contexts.append(value)

    add(event.get("triggerContext"))

    data = event.get("data")
    payload = event.get("payload")
    add(_get_mapping(payload, "triggerContext"))
    add(_get_mapping(data, "triggerContext"))

    add(event.get("issue"))
    add(_get_mapping(data, "issue"))
    add(_get_mapping(payload, "issue"))

    add(data)
    add(payload)
    add(event)

    return contexts


def _get_mapping(value: Any, key: str) -> Mapping[str, Any] | None:
    if isinstance(value, Mapping) and isinstance(value.get(key), Mapping):
        return value[key]
    return None


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    trigger_names = {
        _normalize_words(context.get(key))
        for context in contexts
        for key in _TRIGGER_KEYS
        if key in context
    }
    trigger_names.discard("")

    if any(name in {"status changed", "status change", "statuschanged"} for name in trigger_names):
        return True

    if _status_was_updated(contexts):
        return True

    issue_update_names = {"update", "updated", "issue updated", "updated issue"}
    return any(name in issue_update_names for name in trigger_names) and _status_was_updated(contexts)


def _status_was_updated(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "changedFields", "updated_fields", "changed_fields"):
            if _contains_status_field(context.get(key)):
                return True
        for key in ("updatedFrom", "changes", "changed"):
            if _changes_contain_status_field(context.get(key)):
                return True
    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field_name(value)
    if isinstance(value, Mapping):
        return any(_is_status_field_name(key) for key in value.keys())
    if isinstance(value, (list, tuple, set)):
        return any(_contains_status_field(item) for item in value)
    return False


def _changes_contain_status_field(value: Any) -> bool:
    if isinstance(value, Mapping):
        if any(_is_status_field_name(key) for key in value.keys()):
            return True
        return any(_changes_contain_status_field(item) for item in value.values())
    if isinstance(value, (list, tuple, set)):
        return any(_changes_contain_status_field(item) for item in value)
    return False


def _is_status_field_name(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    compact = _compact_key(value)
    return compact in _STATUS_FIELD_NAMES


def _find_new_status(contexts: list[Mapping[str, Any]]) -> str | None:
    status = _find_first_status_value(contexts, _EXPLICIT_STATUS_KEYS)
    if status is not None:
        return status

    changed_status = _find_changed_to_status(contexts)
    if changed_status is not None:
        return changed_status

    return _find_first_status_value(contexts, _STATUS_KEYS)


def _find_first_status_value(
    contexts: list[Mapping[str, Any]], keys: tuple[str, ...]
) -> str | None:
    for context in contexts:
        for key in keys:
            if key in context:
                status = _status_name(context[key])
                if status is not None:
                    return status
    return None


def _find_changed_to_status(contexts: list[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        for key in ("changes", "changed"):
            status = _changed_to_status(context.get(key))
            if status is not None:
                return status
    return None


def _changed_to_status(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key, change in value.items():
            if _is_status_field_name(key):
                status = _change_to_value(change)
                if status is not None:
                    return status
        for change in value.values():
            status = _changed_to_status(change)
            if status is not None:
                return status

    if isinstance(value, (list, tuple)):
        for item in value:
            if not isinstance(item, Mapping):
                continue
            field_name = (
                item.get("field")
                or item.get("fieldName")
                or item.get("name")
                or item.get("key")
            )
            if _is_status_field_name(field_name):
                status = _change_to_value(item)
                if status is not None:
                    return status
    return None


def _change_to_value(change: Any) -> str | None:
    if isinstance(change, Mapping):
        for key in ("to", "newValue", "new", "after", "value"):
            if key in change:
                status = _status_name(change[key])
                if status is not None:
                    return status
    return _status_name(change)


def _status_name(value: Any) -> str | None:
    if isinstance(value, str):
        status = value.strip()
        return status or None
    if isinstance(value, Mapping):
        for key in ("name", "displayName", "label", "title"):
            if key in value:
                status = _status_name(value[key])
                if status is not None:
                    return status
    return None


def _find_first_text(
    contexts: list[Mapping[str, Any]], keys: tuple[str, ...]
) -> str | None:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if isinstance(value, str):
                text = value.strip()
                if text:
                    return text
    return None


def _normalize_words(value: Any) -> str:
    text = _status_name(value)
    if text is None:
        return ""

    with_spaces = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    normalized = re.sub(r"[^A-Za-z0-9]+", " ", with_spaces).strip().casefold()
    return re.sub(r"\s+", " ", normalized)


def _compact_key(value: str) -> str:
    with_spaces = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    return re.sub(r"[^A-Za-z0-9]+", "", with_spaces).casefold()


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
