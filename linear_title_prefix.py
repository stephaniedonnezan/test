"""Build Linear issue title updates for research status changes.

The automation runner can pass either Cursor's flat ``triggerContext`` payload or
a nested Linear webhook payload. This module keeps the decision logic isolated:
when an issue status changes to "to research", return the title update action;
otherwise return ``None``.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflowstate",
    "workflowstatus",
}
_DIRECT_STATUS_CHANGE_TRIGGERS = {
    "statuschanged",
    "statuschange",
    "statusupdated",
    "statechanged",
    "statechange",
    "workflowstatechanged",
    "workflowstatuschanged",
}
_GENERIC_UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issueupdate",
    "issueupdated",
    "updatedissue",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear issue title update action for matching status changes."""

    if not isinstance(event, Mapping):
        return None

    context = _build_context(event)
    if not context:
        return None

    if not _is_status_change_event(context):
        return None

    status = _extract_new_status(context)
    if _normalize_value(status) != _normalize_value(TARGET_STATUS):
        return None

    issue_id = _first_text(context, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_text(context, ("title", "name"))
    if not issue_id or not title:
        return None

    if _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _build_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common webhook locations with trigger metadata winning conflicts."""

    context: dict[str, Any] = {}
    _merge_mapping(context, _nested_mapping(event, "data", "issue"))
    _merge_mapping(context, _nested_mapping(event, "issue"))
    _merge_mapping(context, _nested_mapping(event, "data"))
    _merge_mapping(context, event)
    _merge_mapping(context, _nested_mapping(event, "triggerContext"))
    return context


def _merge_mapping(target: dict[str, Any], value: Any) -> None:
    if isinstance(value, Mapping):
        target.update(value)


def _nested_mapping(mapping: Mapping[str, Any], *keys: str) -> Any:
    current: Any = mapping
    for key in keys:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current


def _is_status_change_event(context: Mapping[str, Any]) -> bool:
    trigger_values = (
        context.get("trigger"),
        context.get("action"),
        context.get("type"),
        context.get("webhookType"),
        context.get("eventType"),
    )
    normalized_triggers = {_normalize_value(value) for value in trigger_values if value is not None}

    if normalized_triggers & _DIRECT_STATUS_CHANGE_TRIGGERS:
        return True

    if normalized_triggers & _GENERIC_UPDATE_TRIGGERS:
        return _updated_fields_include_status(context)

    return _updated_fields_include_status(context)


def _updated_fields_include_status(context: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        if _field_collection_has_status(context.get(key)):
            return True

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        return any(_normalize_key(key) in _STATUS_FIELD_NAMES for key in changes)

    if isinstance(changes, Sequence) and not isinstance(changes, (str, bytes, bytearray)):
        for change in changes:
            if isinstance(change, Mapping):
                field = change.get("field") or change.get("name") or change.get("key")
                if _normalize_key(field) in _STATUS_FIELD_NAMES:
                    return True
            elif _normalize_key(change) in _STATUS_FIELD_NAMES:
                return True

    return False


def _field_collection_has_status(fields: Any) -> bool:
    if isinstance(fields, str):
        return _normalize_key(fields) in _STATUS_FIELD_NAMES

    if isinstance(fields, Mapping):
        return any(_normalize_key(key) in _STATUS_FIELD_NAMES for key in fields)

    if isinstance(fields, Sequence) and not isinstance(fields, (str, bytes, bytearray)):
        return any(_normalize_key(field) in _STATUS_FIELD_NAMES for field in fields)

    return False


def _extract_new_status(context: Mapping[str, Any]) -> str | None:
    for key in ("newStatus", "new_status", "statusName", "stateName", "workflowStateName"):
        status = _text_or_name(context.get(key))
        if status:
            return status

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        for key, change in changes.items():
            if _normalize_key(key) in _STATUS_FIELD_NAMES:
                status = _change_new_value(change)
                if status:
                    return status

    if isinstance(changes, Sequence) and not isinstance(changes, (str, bytes, bytearray)):
        for change in changes:
            if not isinstance(change, Mapping):
                continue
            field = change.get("field") or change.get("name") or change.get("key")
            if _normalize_key(field) in _STATUS_FIELD_NAMES:
                status = _change_new_value(change)
                if status:
                    return status

    for key in ("status", "state", "workflowState", "workflowStatus"):
        status = _text_or_name(context.get(key))
        if status:
            return status

    return None


def _change_new_value(change: Any) -> str | None:
    if isinstance(change, Mapping):
        for key in ("to", "newValue", "new_value", "after", "value"):
            status = _text_or_name(change.get(key))
            if status:
                return status
    return _text_or_name(change)


def _text_or_name(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            text = _text_or_name(value.get(key))
            if text:
                return text
    return None


def _first_text(context: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        text = _text_or_name(context.get(key))
        if text:
            return text
    return None


def _has_prefix(title: str) -> bool:
    return title.casefold().startswith(TITLE_PREFIX.casefold())


def _normalize_value(value: Any) -> str:
    text = _text_or_name(value)
    if not text:
        return ""

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    return re.sub(r"[^a-z0-9]+", "", spaced.casefold())


def _normalize_key(value: Any) -> str:
    text = _text_or_name(value)
    if not text:
        return ""
    return re.sub(r"[^a-z0-9]+", "", text.casefold())


def main() -> int:
    """Read a JSON event from stdin and print the title update action."""

    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    print(json.dumps(action, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
