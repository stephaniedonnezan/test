"""Build Linear issue-title updates for issues entering research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_DIRECT_STATUS_CHANGE_TRIGGERS = {
    "statuschanged",
    "statuschange",
    "statechanged",
    "statechange",
    "workflowstatechanged",
    "workflowstatechange",
}
_GENERIC_UPDATE_TRIGGERS = {
    "issueupdated",
    "updatedissue",
    "update",
    "updated",
}
_STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow_state"}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title-update action when an issue moves to research.

    The automation payload may be a flat Cursor trigger context or a nested
    Linear webhook shape. This function keeps the side effect out of the module:
    callers can apply the returned action to Linear.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = list(_iter_mappings(event))
    if not _is_status_change_event(contexts):
        return None

    new_status = _find_status(contexts)
    if _normalize_text(new_status) != TARGET_STATUS:
        return None

    issue_id = _find_text(
        contexts,
        ("issueId", "issue_id", "identifier", "key", "id"),
    )
    title = _find_text(contexts, ("title", "name"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if not title or _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _iter_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for child in value.values():
            yield from _iter_mappings(child)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_mappings(item)


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    trigger_values = []
    for context in contexts:
        for key in ("trigger", "webhookType", "webhook_type", "action", "type", "event", "eventType"):
            value = context.get(key)
            if isinstance(value, str):
                trigger_values.append(_compact_text(value))

    if any(value in _DIRECT_STATUS_CHANGE_TRIGGERS for value in trigger_values):
        return True

    if any(value in _GENERIC_UPDATE_TRIGGERS for value in trigger_values):
        return _updated_fields_include_status(contexts)

    return False


def _updated_fields_include_status(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "updated_fields"):
            value = context.get(key)
            if _field_names_include_status(value):
                return True

        changes = context.get("changes")
        if isinstance(changes, Mapping):
            if _field_names_include_status(changes.keys()):
                return True
        elif isinstance(changes, list):
            for change in changes:
                if isinstance(change, Mapping) and _field_names_include_status(
                    (change.get("field"), change.get("name"))
                ):
                    return True

    return False


def _field_names_include_status(value: Any) -> bool:
    if isinstance(value, str):
        values = [value]
    elif isinstance(value, Iterable):
        values = list(value)
    else:
        return False

    return any(
        isinstance(item, str) and _compact_text(item) in _STATUS_FIELD_NAMES
        for item in values
    )


def _find_status(contexts: list[Mapping[str, Any]]) -> str | None:
    explicit_status = _find_text(
        contexts,
        (
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
        ),
    )
    if explicit_status:
        return explicit_status

    status = _find_text(contexts, ("status", "state", "workflowState", "workflow_state"))
    if status:
        return status

    for context in contexts:
        changes = context.get("changes")
        if not isinstance(changes, Mapping):
            continue
        for field in ("status", "state", "workflowState", "workflow_state"):
            value = changes.get(field)
            status = _status_value_from_change(value)
            if status:
                return status

    return None


def _status_value_from_change(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if not isinstance(value, Mapping):
        return None

    return _first_string(
        value.get("to"),
        value.get("toName"),
        value.get("new"),
        value.get("newValue"),
        value.get("name"),
    )


def _find_text(contexts: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            text = _text_from_value(value)
            if text:
                return text
    return None


def _text_from_value(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        return _first_string(value.get("name"), value.get("title"), value.get("id"))
    return None


def _first_string(*values: Any) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value
    return None


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    with_word_boundaries = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value.strip())
    normalized = re.sub(r"[^A-Za-z0-9]+", " ", with_word_boundaries).strip().lower()
    return re.sub(r"\s+", " ", normalized)


def _compact_text(value: str) -> str:
    normalized = _normalize_text(value)
    return "" if normalized is None else normalized.replace(" ", "")


def main() -> int:
    payload = json.load(sys.stdin)
    action = build_issue_title_update(payload)
    if action is not None:
        print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
