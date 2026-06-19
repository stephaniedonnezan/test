"""Build Linear issue title updates for Cursor research status changes.

The automation is intentionally side-effect free: callers pass a webhook or
automation payload, and the module returns the title update to apply.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "toresearch"

STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflowstate",
    "workflowstatus",
    "statusname",
    "statename",
}

DIRECT_STATUS_CHANGE_TRIGGERS = {
    "statuschanged",
    "statuschange",
    "statechanged",
    "statechange",
    "workflowstatechanged",
    "workflowstatechange",
}

GENERIC_UPDATE_TRIGGERS = {
    "issueupdated",
    "updatedissue",
    "update",
    "updated",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return an issue-title update action when an issue moves to To Research.

    The returned shape is deliberately simple so a calling automation can apply
    it through its Linear integration layer.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_change_event(contexts):
        return None

    new_status = _extract_new_status(contexts)
    if _normalize(new_status) != TARGET_STATUS:
        return None

    issue_id = _extract_issue_id(contexts)
    title = _extract_title(contexts)
    if not issue_id or not title:
        return None
    if _has_title_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": _prefixed_title(title),
    }


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return plausible payload contexts, outermost first.

    Linear and Cursor automation payloads may place issue data in top-level
    fields, in triggerContext, or inside data.issue. Keeping all contexts lets
    extraction prefer explicit outer event metadata while still finding nested
    issue details.
    """

    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and not any(value is item for item in contexts):
            contexts.append(value)

    add(event)
    add(event.get("triggerContext"))

    automation_info = event.get("automation_trigger_info")
    if isinstance(automation_info, Mapping):
        add(automation_info)
        add(automation_info.get("triggerContext"))
        trigger_context = automation_info.get("triggerContext")
        if isinstance(trigger_context, Mapping):
            add(trigger_context.get("data"))
            add(trigger_context.get("issue"))

    data = event.get("data")
    if isinstance(data, Mapping):
        add(data)
        add(data.get("issue"))

    add(event.get("issue"))

    # Include one additional nested level for common issue/data wrappers.
    for context in list(contexts):
        add(context.get("data"))
        add(context.get("issue"))

    return contexts


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    trigger_values = (
        "trigger",
        "webhookType",
        "webhook_type",
        "action",
        "type",
        "event",
        "eventType",
        "event_type",
    )

    saw_generic_update = False
    for context in contexts:
        for key in trigger_values:
            normalized = _normalize(context.get(key))
            if normalized in DIRECT_STATUS_CHANGE_TRIGGERS:
                return True
            if normalized in GENERIC_UPDATE_TRIGGERS:
                saw_generic_update = True

    return saw_generic_update and _changed_fields_include_status(contexts)


def _changed_fields_include_status(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        updated_fields = context.get("updatedFields")
        if _iterable_contains_status_field(updated_fields):
            return True

        updated_fields = context.get("updated_fields")
        if _iterable_contains_status_field(updated_fields):
            return True

        changes = context.get("changes")
        if isinstance(changes, Mapping):
            for key, value in changes.items():
                if _normalize(key) in STATUS_FIELD_NAMES:
                    return True
                if isinstance(value, Mapping) and _normalize(value.get("field")) in STATUS_FIELD_NAMES:
                    return True
        elif isinstance(changes, list):
            for item in changes:
                if isinstance(item, Mapping):
                    field = item.get("field") or item.get("name") or item.get("key")
                    if _normalize(field) in STATUS_FIELD_NAMES:
                        return True
                elif _normalize(item) in STATUS_FIELD_NAMES:
                    return True

    return False


def _iterable_contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize(value) in STATUS_FIELD_NAMES

    if not isinstance(value, list | tuple | set):
        return False

    for item in value:
        if isinstance(item, Mapping):
            item = item.get("field") or item.get("name") or item.get("key")
        if _normalize(item) in STATUS_FIELD_NAMES:
            return True

    return False


def _extract_new_status(contexts: list[Mapping[str, Any]]) -> str | None:
    explicit_keys = (
        "newStatus",
        "new_status",
        "statusName",
        "status_name",
        "stateName",
        "state_name",
        "workflowStateName",
        "workflow_state_name",
    )
    for context in contexts:
        value = _first_text(context, explicit_keys)
        if value:
            return value

    for context in contexts:
        value = _status_from_changes(context.get("changes"))
        if value:
            return value

    fallback_keys = ("status", "state", "workflowState", "workflow_state")
    for context in contexts:
        value = _first_text(context, fallback_keys)
        if value:
            return value

    return None


def _status_from_changes(changes: Any) -> str | None:
    if isinstance(changes, Mapping):
        for key, value in changes.items():
            if _normalize(key) not in STATUS_FIELD_NAMES:
                continue
            found = _first_text_from_value(value, ("to", "new", "after", "name"))
            if found:
                return found

    if isinstance(changes, list):
        for item in changes:
            if not isinstance(item, Mapping):
                continue
            field = item.get("field") or item.get("name") or item.get("key")
            if _normalize(field) not in STATUS_FIELD_NAMES:
                continue
            found = _first_text_from_value(item, ("to", "new", "after", "value", "name"))
            if found and _normalize(found) not in STATUS_FIELD_NAMES:
                return found

    return None


def _extract_issue_id(contexts: list[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        value = _first_text(
            context,
            ("issueId", "issue_id", "identifier", "key", "id"),
        )
        if value:
            return value
    return None


def _extract_title(contexts: list[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        value = _first_text(context, ("title", "name"))
        if value:
            return value
    return None


def _first_text(context: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        found = _first_text_from_value(context.get(key), ("name", "title"))
        if found:
            return found
    return None


def _first_text_from_value(value: Any, nested_keys: tuple[str, ...]) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None

    if isinstance(value, Mapping):
        for key in nested_keys:
            found = _first_text_from_value(value.get(key), nested_keys)
            if found:
                return found

    return None


def _prefixed_title(title: str) -> str:
    title = title.strip()
    return f"{TITLE_PREFIX}: {title}"


def _has_title_prefix(title: str) -> bool:
    return title.strip().lower().startswith(TITLE_PREFIX.lower())


def _normalize(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    value = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is None:
        return 0
    json.dump(update, sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
