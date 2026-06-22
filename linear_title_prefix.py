"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflowstatus"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue title update when a Linear issue moves to To Research.

    The function is intentionally side-effect free so the automation runner can
    decide how to apply the returned action to Linear.
    """

    if not isinstance(event, Mapping):
        return None

    context = _event_context(event)
    if not _is_status_change_event(context):
        return None

    if _normalize_status(_target_status(context)) != _normalize_status(TARGET_STATUS):
        return None

    issue_id = _clean_text(_first_value(context, ("issueId", "issue_id", "id", "identifier", "key")))
    title = _clean_text(_first_value(context, ("title", "name")))
    if issue_id is None or title is None or _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def handle_issue_status_changed(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Backward-compatible alias for automation entrypoints."""

    return build_issue_title_update(event)


def _event_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten common Cursor and Linear webhook wrappers into one context."""

    context: dict[str, Any] = {}

    issue = _mapping_at(event, "data", "issue") or _mapping_at(event, "issue")
    if issue is not None:
        context.update(issue)

    data = _mapping_at(event, "data")
    if data is not None:
        context.update({key: value for key, value in data.items() if key != "issue"})

    trigger_context = (
        _mapping_at(event, "automation_trigger_info", "triggerContext")
        or _mapping_at(event, "automationTriggerInfo", "triggerContext")
        or _mapping_at(event, "triggerContext")
    )
    if trigger_context is not None:
        context.update(trigger_context)

    context.update(
        {
            key: value
            for key, value in event.items()
            if key
            not in {
                "automation_trigger_info",
                "automationTriggerInfo",
                "triggerContext",
                "data",
                "issue",
            }
        }
    )
    return context


def _is_status_change_event(context: Mapping[str, Any]) -> bool:
    trigger_values = [
        _normalize_event_name(value)
        for value in _values_for_keys(context, ("trigger", "webhookType", "action", "type"))
        if isinstance(value, str)
    ]

    if any(value in {"statuschanged", "statuschange"} for value in trigger_values):
        return True

    is_generic_update = any(value in {"update", "updated", "issueupdated", "updatedissue"} for value in trigger_values)
    if not is_generic_update:
        return False

    return _mentions_status_field(context.get("updatedFields")) or _mentions_status_field(
        context.get("changes")
    )


def _target_status(context: Mapping[str, Any]) -> Any:
    explicit = _first_value(
        context,
        (
            "newStatus",
            "new_status",
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
    if explicit is not None:
        return explicit

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        changed_status = _status_from_changes(changes)
        if changed_status is not None:
            return changed_status

    return _first_value(context, ("status", "state", "workflowState", "workflowStatus"))


def _status_from_changes(changes: Mapping[str, Any]) -> Any:
    for key, value in changes.items():
        if _normalize_field_name(str(key)) not in STATUS_FIELD_NAMES:
            continue
        if isinstance(value, Mapping):
            for nested_key in ("to", "new", "after", "name"):
                if nested_key in value:
                    return value[nested_key]
        return value
    return None


def _mentions_status_field(value: Any) -> bool:
    if value is None:
        return False

    if isinstance(value, str):
        return _normalize_field_name(value) in STATUS_FIELD_NAMES

    if isinstance(value, Mapping):
        return any(_normalize_field_name(str(key)) in STATUS_FIELD_NAMES for key in value)

    if isinstance(value, (list, tuple, set)):
        return any(_mentions_status_field(item) for item in value)

    return False


def _first_value(context: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key not in context:
            continue
        value = context[key]
        if isinstance(value, Mapping):
            if "name" in value:
                return value["name"]
            if "title" in value:
                return value["title"]
        return value
    return None


def _values_for_keys(context: Mapping[str, Any], keys: tuple[str, ...]) -> list[Any]:
    return [context[key] for key in keys if key in context]


def _mapping_at(mapping: Mapping[str, Any], *keys: str) -> Mapping[str, Any] | None:
    current: Any = mapping
    for key in keys:
        if not isinstance(current, Mapping) or key not in current:
            return None
        current = current[key]
    return current if isinstance(current, Mapping) else None


def _clean_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def _normalize_status(value: Any) -> str:
    if isinstance(value, Mapping):
        value = value.get("name")
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^a-z0-9]+", "", _split_camel_case(value).lower())


def _normalize_event_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", _split_camel_case(value).lower())


def _normalize_field_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", _split_camel_case(value).lower())


def _split_camel_case(value: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is None:
        return 0
    print(json.dumps(action, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
