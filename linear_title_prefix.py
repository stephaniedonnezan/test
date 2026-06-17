"""Build Linear issue title updates for Cursor research automation.

The automation trigger supplies a JSON event.  When that event represents a
Linear issue status change to "to research", this module returns the title
update action expected by the surrounding automation.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


PREFIX = "Cursor researching"
STATUS_TARGET = "to research"

_TRIGGER_KEYS = ("trigger", "webhookType", "action", "type", "eventType")
_EXPLICIT_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "toStatus",
    "to_status",
    "statusTo",
    "status_to",
    "newState",
    "new_state",
    "toState",
    "to_state",
    "newWorkflowState",
    "new_workflow_state",
)
_CURRENT_STATUS_KEYS = ("status", "state", "workflowState", "workflow_state")
_ISSUE_ID_KEYS = ("issueId", "issue_id", "id", "identifier", "key")
_TITLE_KEYS = ("title", "name")
_UPDATED_FIELD_KEYS = (
    "updatedFields",
    "updated_fields",
    "changedFields",
    "changed_fields",
    "changes",
)
_STATUS_FIELD_NAMES = {"status", "state", "workflow state", "workflowstate"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when a payload enters research."""
    if not isinstance(event, Mapping):
        return None

    candidates = _candidate_maps(event)
    if not _is_status_change_event(event, candidates):
        return None

    new_status = _extract_new_status(candidates)
    if _normalize_words(new_status) != STATUS_TARGET:
        return None

    issue_id = _first_text(candidates, _ISSUE_ID_KEYS)
    title = _first_text(candidates, _TITLE_KEYS)
    if not issue_id or not title:
        return None

    issue_id = issue_id.strip()
    title = title.strip()
    if not issue_id or not title:
        return None

    if title.casefold().startswith(PREFIX.casefold()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _candidate_maps(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return likely payload containers in precedence order."""
    candidates: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in candidates:
            candidates.append(value)

    add(event)

    for key in ("triggerContext", "trigger_context", "payload", "data", "issue"):
        value = event.get(key)
        add(value)
        if isinstance(value, Mapping):
            for nested_key in ("payload", "data", "issue"):
                nested = value.get(nested_key)
                add(nested)
                if isinstance(nested, Mapping):
                    add(nested.get("issue"))

    return candidates


def _is_status_change_event(
    event: Mapping[str, Any], candidates: Sequence[Mapping[str, Any]]
) -> bool:
    trigger_names = {
        _normalize_words(candidate.get(key))
        for candidate in candidates
        for key in _TRIGGER_KEYS
        if candidate.get(key) is not None
    }
    trigger_names.discard("")

    if any(name in {"status changed", "status change"} for name in trigger_names):
        return True
    if any(
        "status changed" in name or "status change" in name for name in trigger_names
    ):
        return True

    generic_update = any(
        name in {"update", "updated", "issue update", "issue updated", "updated issue"}
        for name in trigger_names
    )
    issue_webhook = "issue" in trigger_names

    return _updated_fields_include_status(event) and (generic_update or issue_webhook)


def _extract_new_status(candidates: Sequence[Mapping[str, Any]]) -> str | None:
    for candidate in candidates:
        for key in _EXPLICIT_STATUS_KEYS:
            status = _status_name(candidate.get(key))
            if status:
                return status

    for candidate in candidates:
        status = _status_from_changes(candidate)
        if status:
            return status

    for candidate in candidates:
        for key in _CURRENT_STATUS_KEYS:
            status = _status_name(candidate.get(key))
            if status:
                return status

    return None


def _status_from_changes(candidate: Mapping[str, Any]) -> str | None:
    for key in _UPDATED_FIELD_KEYS:
        changes = candidate.get(key)
        status = _status_from_change_value(changes)
        if status:
            return status
    return None


def _status_from_change_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        field = value.get("field") or value.get("name") or value.get("key")
        if field is not None and _is_status_field(field):
            status = _status_from_transition(value)
            if status:
                return status

        for key, nested in value.items():
            if _is_status_field(key):
                status = _status_from_transition(nested)
                if status:
                    return status
            status = _status_from_change_value(nested)
            if status:
                return status
        return None

    if _is_sequence(value):
        for item in value:
            if isinstance(item, str) and _is_status_field(item):
                continue
            status = _status_from_change_value(item)
            if status:
                return status
        return None

    return None


def _status_from_transition(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in (
            "to",
            "toValue",
            "to_value",
            "new",
            "newValue",
            "new_value",
            "after",
            "name",
            "value",
        ):
            status = _status_name(value.get(key))
            if status:
                return status
        return None
    return _status_name(value)


def _updated_fields_include_status(event: Mapping[str, Any]) -> bool:
    return any(_updated_value_mentions_status(value) for value in _walk(event))


def _updated_value_mentions_status(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key in _UPDATED_FIELD_KEYS:
            if key in value and _change_container_mentions_status(value[key]):
                return True
        return False
    return False


def _change_container_mentions_status(value: Any) -> bool:
    if isinstance(value, Mapping):
        field = value.get("field") or value.get("name") or value.get("key")
        if field is not None and _is_status_field(field):
            return True
        return any(
            _is_status_field(key) or _change_container_mentions_status(nested)
            for key, nested in value.items()
        )

    if _is_sequence(value):
        return any(
            _is_status_field(item)
            if isinstance(item, str)
            else _change_container_mentions_status(item)
            for item in value
        )

    return _is_status_field(value)


def _walk(value: Any) -> Sequence[Any]:
    values: list[Any] = []

    def add(current: Any) -> None:
        values.append(current)
        if isinstance(current, Mapping):
            for child in current.values():
                add(child)
        elif _is_sequence(current):
            for child in current:
                add(child)

    add(value)
    return values


def _first_text(candidates: Sequence[Mapping[str, Any]], keys: Sequence[str]) -> str | None:
    for candidate in candidates:
        for key in keys:
            value = candidate.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _status_name(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        for key in ("name", "title", "label", "value"):
            nested = value.get(key)
            if isinstance(nested, str) and nested.strip():
                return nested
    return None


def _is_status_field(value: Any) -> bool:
    return _normalize_words(value).replace(" ", "") in {
        name.replace(" ", "") for name in _STATUS_FIELD_NAMES
    }


def _normalize_words(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    with_spaces = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    words_only = re.sub(r"[^A-Za-z0-9]+", " ", with_spaces)
    return " ".join(words_only.casefold().split())


def _is_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))


def main() -> int:
    result = build_issue_title_update(json.load(sys.stdin))
    json.dump(result, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
