"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_CHANGE_TOKENS = {
    "statuschange",
    "statuschanged",
    "statechange",
    "statechanged",
    "workflowstatechange",
    "workflowstatechanged",
}
_UPDATE_TOKENS = {"update", "updated", "issueupdate", "issueupdated", "updatedissue"}
_STATUS_FIELD_TOKENS = {
    "status",
    "statusid",
    "state",
    "stateid",
    "workflowstate",
    "workflowstateid",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear issue title update action when an issue enters research."""

    if not isinstance(event, Mapping):
        return None

    contexts = _collect_contexts(event)
    if not _is_status_change_event(contexts):
        return None

    new_status = _extract_new_status(contexts)
    if _normalize_token(new_status) != _normalize_token(TARGET_STATUS):
        return None

    issue_id = _extract_issue_id(contexts)
    title = _extract_title(contexts)
    if not issue_id or not title:
        return None

    trimmed_title = title.strip()
    if _has_title_prefix(trimmed_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {trimmed_title}",
    }


def _collect_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []

    automation_info = _mapping_value(event, "automation_trigger_info", "automationTriggerInfo")
    trigger_context = _mapping_value(event, "triggerContext", "trigger_context")
    data = _mapping_value(event, "data")
    issue = _mapping_value(event, "issue")

    if automation_info:
        automation_trigger_context = _mapping_value(
            automation_info, "triggerContext", "trigger_context"
        )
        if automation_trigger_context:
            contexts.append(automation_trigger_context)

    if trigger_context:
        contexts.append(trigger_context)

    if data:
        data_issue = _mapping_value(data, "issue")
        if data_issue:
            contexts.append(data_issue)
        contexts.append(data)

    if issue:
        contexts.append(issue)

    contexts.append(event)
    return contexts


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    saw_generic_update = False
    saw_status_changed = False

    for context in contexts:
        for key in ("trigger", "webhookType", "webhook_type", "action", "type", "eventType"):
            token = _normalize_token(context.get(key))
            if token in _STATUS_CHANGE_TOKENS:
                saw_status_changed = True
            if token in _UPDATE_TOKENS:
                saw_generic_update = True

    if saw_status_changed:
        return True

    return saw_generic_update and _updated_fields_include_status(contexts)


def _updated_fields_include_status(contexts: Iterable[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            fields = context.get(key)
            if _field_collection_includes_status(fields):
                return True

        for key in ("changes", "changed", "updatedFrom", "updated_from"):
            changes = context.get(key)
            if isinstance(changes, Mapping) and _field_collection_includes_status(changes.keys()):
                return True

    return False


def _field_collection_includes_status(fields: Any) -> bool:
    if isinstance(fields, Mapping):
        candidates = fields.keys()
    elif isinstance(fields, str):
        candidates = re.split(r"[\s,]+", fields)
    elif isinstance(fields, Iterable):
        candidates = fields
    else:
        return False

    return any(_normalize_token(field) in _STATUS_FIELD_TOKENS for field in candidates)


def _extract_new_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    status_from_changes = _status_from_changes(contexts)
    if status_from_changes:
        return status_from_changes

    for context in contexts:
        for key in (
            "newStatus",
            "new_status",
            "newState",
            "new_state",
            "toStatus",
            "to_status",
            "status",
            "state",
            "workflowState",
            "workflow_state",
        ):
            value = _string_from_value(context.get(key))
            if value:
                return value

    return None


def _status_from_changes(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        for key in ("changes", "changed"):
            changes = context.get(key)
            if not isinstance(changes, Mapping):
                continue

            for field, change in changes.items():
                if _normalize_token(field) not in _STATUS_FIELD_TOKENS:
                    continue

                value = _string_from_change(change)
                if value:
                    return value

    return None


def _string_from_change(change: Any) -> str | None:
    if isinstance(change, Mapping):
        for key in ("to", "newValue", "new_value", "after", "name", "value"):
            value = _string_from_value(change.get(key))
            if value:
                return value
    return _string_from_value(change)


def _extract_issue_id(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        for key in ("issueId", "issue_id", "identifier", "key", "id"):
            value = _string_from_value(context.get(key))
            if value:
                return value
    return None


def _extract_title(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        value = _string_from_value(context.get("title"))
        if value:
            return value
    return None


def _mapping_value(mapping: Mapping[str, Any], *keys: str) -> Mapping[str, Any] | None:
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, Mapping):
            return value
    return None


def _string_from_value(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "label", "value"):
            nested = _string_from_value(value.get(key))
            if nested:
                return nested

    return None


def _has_title_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def _normalize_token(value: Any) -> str:
    text = _string_from_value(value) or ""
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def main() -> int:
    update = build_issue_title_update(json.load(sys.stdin))
    print(json.dumps(update, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
