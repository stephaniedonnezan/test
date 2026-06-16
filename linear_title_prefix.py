"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


TITLE_MARKER = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {"status", "state", "workflowstate"}
_EXPLICIT_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "toStatus",
    "statusTo",
    "newState",
    "new_state",
    "toState",
    "stateTo",
    "newWorkflowState",
    "new_workflow_state",
    "toWorkflowState",
    "workflowStateTo",
)
_CURRENT_STATUS_KEYS = (
    "status",
    "state",
    "workflowState",
    "workflow_state",
)
_ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "key", "id")
_TITLE_KEYS = ("title", "name")


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to To Research.

    The handler accepts both Cursor automation trigger payloads and Linear-style
    nested issue update webhooks. It returns a serializable action for the caller
    to execute, or ``None`` when the event does not require a title change.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _context_candidates(event)
    if not _is_status_change_event(contexts):
        return None

    status = _changed_status(contexts)
    if _normalize_status(status) != _normalize_status(TARGET_STATUS):
        return None

    issue_id = _first_text(contexts, _ISSUE_ID_KEYS)
    title = _first_text(contexts, _TITLE_KEYS)
    if not issue_id or not title:
        return None

    if _has_researching_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_MARKER}: {title}",
    }


def _context_candidates(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []

    trigger_context = _mapping_value(event, "triggerContext")
    data = _mapping_value(event, "data")
    issue = _mapping_value(event, "issue")

    _append_mapping(contexts, trigger_context)
    _append_mapping(contexts, _mapping_value(data, "issue"))
    _append_mapping(contexts, _mapping_value(data, "data"))
    _append_mapping(contexts, issue)
    _append_mapping(contexts, data)
    _append_mapping(contexts, event)

    return contexts


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("trigger", "eventType", "event_type", "action", "type", "webhookType"):
            trigger_value = _normalize_token(context.get(key))
            if _is_direct_status_change_trigger(trigger_value):
                return True

    if _status_field_was_updated(contexts):
        return True

    return False


def _is_direct_status_change_trigger(value: str) -> bool:
    return (
        "statuschanged" in value
        or "statechanged" in value
        or "workflowstatechanged" in value
        or (("status" in value or "state" in value) and "change" in value)
    )


def _status_field_was_updated(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            if _contains_status_field(context.get(key)):
                return True

        for key in ("changes", "updatedFrom", "updated_from", "previousValues"):
            value = context.get(key)
            if isinstance(value, Mapping) and any(
                _normalize_field_name(field) in _STATUS_FIELD_NAMES for field in value
            ):
                return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_field_name(value) in _STATUS_FIELD_NAMES

    if isinstance(value, Mapping):
        return any(
            _normalize_field_name(key) in _STATUS_FIELD_NAMES
            or _contains_status_field(nested_value)
            for key, nested_value in value.items()
        )

    if isinstance(value, list | tuple | set):
        return any(_contains_status_field(item) for item in value)

    return False


def _changed_status(contexts: list[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        status = _first_text([context], _EXPLICIT_STATUS_KEYS)
        if status:
            return status

    for context in contexts:
        status = _status_from_change_mapping(context)
        if status:
            return status

    for context in contexts:
        status = _first_text([context], _CURRENT_STATUS_KEYS)
        if status:
            return status

    return None


def _status_from_change_mapping(context: Mapping[str, Any]) -> str | None:
    for container_key in ("changes",):
        container = context.get(container_key)
        if not isinstance(container, Mapping):
            continue

        for field, value in container.items():
            if _normalize_field_name(field) not in _STATUS_FIELD_NAMES:
                continue

            status = _change_target_value(value)
            if status:
                return status

    return None


def _change_target_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in (
            "to",
            "new",
            "newValue",
            "new_value",
            "after",
            "value",
            "name",
            "title",
        ):
            text = _text_value(value.get(key))
            if text:
                return text
        return None

    return _text_value(value)


def _first_text(contexts: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for context in contexts:
        for key in keys:
            value = _text_value(context.get(key))
            if value:
                return value

    return None


def _text_value(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None

    if isinstance(value, int):
        return str(value)

    if isinstance(value, Mapping):
        for key in ("name", "title", "label", "id", "identifier", "key"):
            text = _text_value(value.get(key))
            if text:
                return text

    return None


def _mapping_value(mapping: Mapping[str, Any] | None, key: str) -> Mapping[str, Any] | None:
    if not isinstance(mapping, Mapping):
        return None

    value = mapping.get(key)
    if isinstance(value, Mapping):
        return value

    return None


def _append_mapping(
    contexts: list[Mapping[str, Any]], mapping: Mapping[str, Any] | None
) -> None:
    if isinstance(mapping, Mapping) and mapping not in contexts:
        contexts.append(mapping)


def _has_researching_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_MARKER.lower())


def _normalize_status(value: Any) -> str:
    return _normalize_token(value)


def _normalize_field_name(value: Any) -> str:
    return _normalize_token(value)


def _normalize_token(value: Any) -> str:
    text = _text_value(value)
    if not text:
        return ""

    with_spaces = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    return re.sub(r"[^a-z0-9]+", "", with_spaces.lower())


def main() -> int:
    payload = json.load(sys.stdin)
    update = build_issue_title_update(payload)
    json.dump(update, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
