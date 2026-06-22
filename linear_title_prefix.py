"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


RESEARCH_STATUS = "to research"
TITLE_PREFIX = "Cursor researching"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow status"}
STATUS_VALUE_KEYS = (
    "newStatus",
    "new_status",
    "status",
    "statusName",
    "state",
    "stateName",
    "workflowState",
    "workflowStateName",
)
TITLE_KEYS = ("title", "name", "summary")
ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "key", "id")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return the Linear title update requested by a matching status change.

    The automation input can arrive as a flat Cursor trigger context, a wrapped
    ``automation_trigger_info.triggerContext`` payload, or a nested Linear issue
    webhook. Non-status changes and non-research statuses are ignored.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _candidate_contexts(event)
    if not any(_is_status_change(context) for context in contexts):
        return None

    if _normalize_status(_extract_new_status(contexts)) != RESEARCH_STATUS:
        return None

    issue_id = _first_text(contexts, ISSUE_ID_KEYS)
    title = _first_text(contexts, TITLE_KEYS)
    if not issue_id or not title or _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _candidate_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return payload mappings in priority order from broad to nested."""

    contexts: list[Mapping[str, Any]] = []
    _append_mapping(contexts, event)

    automation_info = event.get("automation_trigger_info")
    if isinstance(automation_info, Mapping):
        _append_mapping(contexts, automation_info)
        _append_mapping(contexts, automation_info.get("triggerContext"))

    _append_mapping(contexts, event.get("triggerContext"))
    data = event.get("data")
    if isinstance(data, Mapping):
        _append_mapping(contexts, data)
        _append_mapping(contexts, data.get("issue"))
        _append_mapping(contexts, data.get("state"))
        _append_mapping(contexts, data.get("workflowState"))

    _append_mapping(contexts, event.get("issue"))
    _append_mapping(contexts, event.get("state"))
    _append_mapping(contexts, event.get("workflowState"))

    changes = event.get("changes")
    if isinstance(changes, Mapping):
        _append_mapping(contexts, changes)
        for key in ("status", "state", "workflowState"):
            _append_mapping(contexts, changes.get(key))

    return contexts


def _append_mapping(
    contexts: list[Mapping[str, Any]], value: Any
) -> None:
    if isinstance(value, Mapping) and not any(value is context for context in contexts):
        contexts.append(value)


def _is_status_change(context: Mapping[str, Any]) -> bool:
    trigger_values = _trigger_values(context)
    if any(_is_status_changed_name(value) for value in trigger_values):
        return True

    if any(_is_generic_issue_update(value) for value in trigger_values):
        return _mentions_status_field(context)

    return False


def _trigger_values(context: Mapping[str, Any]) -> list[str]:
    values: list[str] = []
    for key in ("trigger", "webhookType", "action", "type"):
        value = context.get(key)
        if isinstance(value, str):
            values.append(value)
    return values


def _is_status_changed_name(value: str) -> bool:
    normalized = _normalize_token(value)
    return normalized in {
        "statuschanged",
        "statuschange",
        "statechanged",
        "statechange",
        "workflowstatechanged",
        "workflowstatechange",
    }


def _is_generic_issue_update(value: str) -> bool:
    normalized = _normalize_token(value)
    return normalized in {
        "update",
        "updated",
        "issueupdate",
        "issueupdated",
        "updatedissue",
    }


def _mentions_status_field(context: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields"):
        fields = context.get(key)
        if _iterable_mentions_status(fields):
            return True

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        if any(_is_status_field(key) for key in changes.keys()):
            return True
        for value in changes.values():
            if isinstance(value, Mapping) and _mapping_mentions_status(value):
                return True

    return _mapping_mentions_status(context)


def _iterable_mentions_status(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)
    if not isinstance(value, Iterable) or isinstance(value, Mapping):
        return False
    return any(isinstance(field, str) and _is_status_field(field) for field in value)


def _mapping_mentions_status(value: Mapping[str, Any]) -> bool:
    return any(_is_status_field(key) for key in value.keys())


def _is_status_field(value: str) -> bool:
    return _normalize_token(value) in STATUS_FIELDS


def _extract_new_status(contexts: list[Mapping[str, Any]]) -> Any:
    for context in contexts:
        for key in ("newStatus", "new_status", "to", "after"):
            value = _status_text(context.get(key))
            if value:
                return value

        changes = context.get("changes")
        if isinstance(changes, Mapping):
            value = _extract_status_from_changes(changes)
            if value:
                return value

    for context in contexts:
        for key in STATUS_VALUE_KEYS:
            value = _status_text(context.get(key))
            if value:
                return value

    return None


def _extract_status_from_changes(changes: Mapping[str, Any]) -> str | None:
    for key in ("status", "state", "workflowState"):
        value = changes.get(key)
        if isinstance(value, Mapping):
            for nested_key in ("newValue", "new_value", "to", "after", "name"):
                status = _status_text(value.get(nested_key))
                if status:
                    return status
        else:
            status = _status_text(value)
            if status:
                return status
    return None


def _status_text(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, Mapping):
        for key in ("name", "title", "value"):
            nested = value.get(key)
            if isinstance(nested, str) and nested.strip():
                return nested.strip()
    return None


def _first_text(contexts: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _has_research_prefix(title: str) -> bool:
    return title.strip().lower().startswith(TITLE_PREFIX.lower())


def _normalize_status(value: Any) -> str | None:
    status = _status_text(value)
    if not status:
        return None
    return re.sub(r"[\s_-]+", " ", _split_camel_case(status)).strip().lower()


def _normalize_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", _split_camel_case(value).lower())


def _split_camel_case(value: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is None:
        return 0
    json.dump(update, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
