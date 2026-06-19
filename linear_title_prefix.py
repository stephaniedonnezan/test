"""Build Linear issue title updates for research-status automation payloads."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow_state"}
_TRIGGER_KEYS = {"trigger", "action", "type", "webhooktype", "webhook_type", "eventtype", "event_type"}
_NEW_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "status",
    "state",
    "workflowState",
    "workflow_state",
)
_ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "key", "id")
_TITLE_KEYS = ("title", "issueTitle", "issue_title", "name")


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return an issue-title update action when a Linear issue moves to research."""

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change(event):
        return None

    if not _is_target_status(_get_new_status(event)):
        return None

    issue = _issue_payload(event)
    issue_id = _string_from_keys(issue, _ISSUE_ID_KEYS)
    title = _string_from_keys(issue, _TITLE_KEYS)
    if not issue_id or not title:
        return None

    if _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title.strip()}",
    }


def _is_status_change(event: Mapping[str, Any]) -> bool:
    trigger_values = list(_values_for_keys(event, _TRIGGER_KEYS))
    if any(_is_direct_status_change(value) for value in trigger_values):
        return True

    if any(_is_generic_issue_update(value) for value in trigger_values):
        return _updated_fields_include_status(event) or _changes_include_status(event)

    return False


def _get_new_status(event: Mapping[str, Any]) -> Any:
    contexts = _contexts(event)
    for context in contexts:
        for key in ("newStatus", "new_status", "statusName", "status_name", "stateName", "state_name"):
            value = context.get(key)
            if value:
                return value

    changes_value = _status_from_changes(event)
    if changes_value:
        return changes_value

    for context in contexts:
        value = _value_from_keys(context, _NEW_STATUS_KEYS)
        if value:
            return value

    return None


def _issue_payload(event: Mapping[str, Any]) -> Mapping[str, Any]:
    merged: dict[str, Any] = {}

    for context in reversed(_contexts(event)):
        issue = _mapping_from_keys(context, ("issue",))
        if issue:
            merged.update(issue)
        merged.update(context)

    return merged


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = [event]
    for key in ("triggerContext", "trigger_context", "data", "issue"):
        value = event.get(key)
        if isinstance(value, Mapping):
            contexts.append(value)

    trigger_context = _mapping_from_keys(event, ("triggerContext", "trigger_context"))
    if trigger_context:
        for key in ("data", "issue"):
            value = trigger_context.get(key)
            if isinstance(value, Mapping):
                contexts.append(value)

    data = _mapping_from_keys(event, ("data",))
    if data:
        for key in ("issue", "state", "workflowState", "workflow_state"):
            value = data.get(key)
            if isinstance(value, Mapping):
                contexts.append(value)

    issue = _mapping_from_keys(event, ("issue",))
    if issue:
        for key in ("state", "workflowState", "workflow_state"):
            value = issue.get(key)
            if isinstance(value, Mapping):
                contexts.append(value)

    return contexts


def _values_for_keys(value: Any, normalized_keys: set[str]) -> Iterable[Any]:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if _normalize_key(key) in normalized_keys:
                yield child
            yield from _values_for_keys(child, normalized_keys)
    elif isinstance(value, list):
        for child in value:
            yield from _values_for_keys(child, normalized_keys)


def _updated_fields_include_status(event: Mapping[str, Any]) -> bool:
    for value in _values_for_keys(event, {"updatedfields", "updated_fields", "changedfields", "changed_fields"}):
        if _field_list_includes_status(value):
            return True
    return False


def _changes_include_status(event: Mapping[str, Any]) -> bool:
    for changes in _values_for_keys(event, {"changes", "changed"}):
        if isinstance(changes, Mapping):
            if any(_normalize_key(key) in _STATUS_FIELD_NAMES for key in changes):
                return True
        elif _field_list_includes_status(changes):
            return True
    return False


def _status_from_changes(event: Mapping[str, Any]) -> Any:
    for changes in _values_for_keys(event, {"changes", "changed"}):
        if not isinstance(changes, Mapping):
            continue

        for key, value in changes.items():
            if _normalize_key(key) not in _STATUS_FIELD_NAMES:
                continue
            if isinstance(value, Mapping):
                for next_key in ("to", "new", "after", "name"):
                    next_value = value.get(next_key)
                    if next_value:
                        return next_value
            elif value:
                return value

    return None


def _field_list_includes_status(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_key(value) in _STATUS_FIELD_NAMES
    if isinstance(value, Mapping):
        return any(_normalize_key(key) in _STATUS_FIELD_NAMES for key in value)
    if isinstance(value, Iterable):
        return any(_field_list_includes_status(item) for item in value)
    return False


def _value_from_keys(mapping: Mapping[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, Mapping):
            for nested_key in ("name", "title"):
                nested_value = value.get(nested_key)
                if nested_value:
                    return nested_value
        elif value:
            return value
    return None


def _string_from_keys(mapping: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    value = _value_from_keys(mapping, keys)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _mapping_from_keys(mapping: Mapping[str, Any], keys: Iterable[str]) -> Mapping[str, Any] | None:
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, Mapping):
            return value
    return None


def _is_target_status(value: Any) -> bool:
    return _compact(value) == _compact(TARGET_STATUS)


def _is_direct_status_change(value: Any) -> bool:
    compacted = _compact(value)
    return compacted in {"statuschanged", "statuschange", "statechanged", "workflowstatechanged"}


def _is_generic_issue_update(value: Any) -> bool:
    compacted = _compact(value)
    return compacted in {"update", "updated", "issueupdate", "issueupdated", "updatedissue"}


def _has_prefix(title: str) -> bool:
    return title.strip().lower().startswith(PREFIX.lower())


def _compact(value: Any) -> str:
    text = str(value)
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def _normalize_key(value: Any) -> str:
    return _compact(value)


def main() -> int:
    """Read a JSON event from stdin and print the computed title update."""

    update = build_issue_title_update(json.load(sys.stdin))
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
