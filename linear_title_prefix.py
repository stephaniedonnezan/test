"""Build Linear issue title updates for research status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TITLE_PREFIX_WITH_SEPARATOR = f"{TITLE_PREFIX}: "
TARGET_STATUS = "to research"
TITLE_UPDATE_ACTION = "update_issue_title"

_STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}
_STATUS_CHANGE_TRIGGERS = {"statuschanged", "statuschange", "statusupdated", "statusupdate"}
_GENERIC_UPDATE_TRIGGERS = {"update", "updated", "issueupdated", "updatedissue"}


def build_issue_title_update(event: Any) -> dict[str, str] | None:
    """Return a Linear issue title update action when an issue enters research."""

    if not isinstance(event, Mapping):
        return None

    context = _issue_context(event)
    if not _is_status_change_event(context):
        return None

    new_status = _extract_status(context)
    if _normalize_text(new_status) != _normalize_text(TARGET_STATUS):
        return None

    issue_id = _first_text(context, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_text(context, ("title", "name"))
    if not issue_id or not title:
        return None

    if _has_research_prefix(title):
        return None

    return {
        "action": TITLE_UPDATE_ACTION,
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX_WITH_SEPARATOR}{title}",
    }


def _issue_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common Linear/Cursor nesting shapes into one lookup context."""

    context: dict[str, Any] = {}

    for wrapper_key in ("automation_trigger_info", "automationTriggerInfo"):
        wrapper = event.get(wrapper_key)
        if isinstance(wrapper, Mapping):
            context.update(_issue_context(wrapper))

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        context.update(_nested_issue_context(trigger_context))
        context.update(trigger_context)

    context.update(_nested_issue_context(event))
    context.update(event)
    return context


def _nested_issue_context(mapping: Mapping[str, Any]) -> dict[str, Any]:
    context: dict[str, Any] = {}

    data = mapping.get("data")
    if isinstance(data, Mapping):
        context.update(data)
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            context.update(issue)

    issue = mapping.get("issue")
    if isinstance(issue, Mapping):
        context.update(issue)

    return context


def _is_status_change_event(context: Mapping[str, Any]) -> bool:
    trigger_values = [
        context.get("trigger"),
        context.get("webhookType"),
        context.get("action"),
        context.get("type"),
    ]

    normalized_triggers = {_normalize_token(value) for value in trigger_values if value}
    if normalized_triggers & _STATUS_CHANGE_TRIGGERS:
        return True

    if normalized_triggers & _GENERIC_UPDATE_TRIGGERS:
        return _changed_fields_include_status(context)

    return False


def _changed_fields_include_status(context: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        if _contains_status_field(context.get(key)):
            return True

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        return any(_normalize_field_name(field) in _STATUS_FIELDS for field in changes)

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_field_name(value) in _STATUS_FIELDS

    if isinstance(value, Iterable) and not isinstance(value, (str, bytes, Mapping)):
        return any(_normalize_field_name(item) in _STATUS_FIELDS for item in value)

    return False


def _extract_status(context: Mapping[str, Any]) -> str | None:
    for key in ("newStatus", "new_status", "statusName", "status_name", "newState", "new_state"):
        value = _string_or_name(context.get(key))
        if value:
            return value

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        for field, change in changes.items():
            if _normalize_field_name(field) in _STATUS_FIELDS:
                value = _changed_value(change)
                if value:
                    return value

    for key in ("status", "state", "workflowState", "workflow_state"):
        value = _string_or_name(context.get(key))
        if value:
            return value

    return None


def _changed_value(change: Any) -> str | None:
    if isinstance(change, Mapping):
        for key in ("newValue", "new_value", "to", "after", "name"):
            value = _string_or_name(change.get(key))
            if value:
                return value

    return _string_or_name(change)


def _string_or_name(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None

    if isinstance(value, Mapping):
        for key in ("name", "label", "title"):
            nested_value = value.get(key)
            if isinstance(nested_value, str) and nested_value.strip():
                return nested_value.strip()

    return None


def _first_text(context: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = context.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def _normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return _normalize_token(value)


def _normalize_token(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    camel_split = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return re.sub(r"[^a-z0-9]+", "", camel_split.lower())


def _normalize_field_name(value: Any) -> str:
    return _normalize_token(str(value)) if value is not None else ""


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        json.dump(update, sys.stdout)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
