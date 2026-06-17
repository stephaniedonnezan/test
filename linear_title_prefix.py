"""Build Linear issue title updates for research status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when an issue moves to To Research."""
    if not isinstance(event, Mapping):
        return None

    context = _event_context(event)
    if not _is_status_change_event(context):
        return None

    new_status = _new_status(context)
    if _normalize_status(new_status) != TARGET_STATUS:
        return None

    issue_id = _first_text(context, ("issueId", "issue_id", "id", "identifier", "key"))
    title = _first_text(context, ("title", "name"))
    if not issue_id or not title:
        return None

    if title.lower().startswith(PREFIX.lower()):
        prefixed_title = title
    else:
        prefixed_title = f"{PREFIX}: {title}"

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": prefixed_title,
    }


def _event_context(event: Mapping[str, Any]) -> dict[str, Any]:
    context: dict[str, Any] = {}

    def merge_mapping(value: Any) -> None:
        if isinstance(value, Mapping):
            context.update(value)

    data = event.get("data")
    issue = data.get("issue") if isinstance(data, Mapping) else None
    merge_mapping(issue)
    merge_mapping(data)
    trigger_context = event.get("triggerContext")
    merge_mapping(trigger_context)
    merge_mapping(event)
    return context


def _is_status_change_event(context: Mapping[str, Any]) -> bool:
    event_names = (
        _normalize_event_name(value)
        for value in (
            context.get("trigger"),
            context.get("webhookType"),
            context.get("action"),
            context.get("type"),
        )
        if isinstance(value, str)
    )

    saw_issue_update = False
    for event_name in event_names:
        if event_name in {"statuschanged", "statechanged", "workflowstatechanged"}:
            return True
        if event_name in {"issueupdated", "updatedissue", "update", "updated"}:
            saw_issue_update = True

    return saw_issue_update and _updated_status_field(context)


def _updated_status_field(context: Mapping[str, Any]) -> bool:
    updated_fields = context.get("updatedFields")
    if isinstance(updated_fields, str):
        updated_fields = [updated_fields]
    if isinstance(updated_fields, list):
        return any(_normalize_field_name(field) in STATUS_FIELDS for field in updated_fields)

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        return any(_normalize_field_name(field) in STATUS_FIELDS for field in changes)

    return False


def _new_status(context: Mapping[str, Any]) -> Any:
    for key in ("newStatus", "new_status", "statusName", "stateName", "workflowStateName"):
        value = context.get(key)
        if value:
            return value

    for key in ("status", "state", "workflowState", "workflow_state"):
        value = context.get(key)
        if isinstance(value, Mapping):
            name = value.get("name")
            if name:
                return name
        elif value:
            return value

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        for key in ("status", "state", "workflowState", "workflow_state"):
            value = changes.get(key)
            if isinstance(value, Mapping):
                for nested_key in ("newValue", "new", "to", "name"):
                    nested_value = value.get(nested_key)
                    if isinstance(nested_value, Mapping):
                        nested_value = nested_value.get("name")
                    if nested_value:
                        return nested_value
            elif value:
                return value

    return None


def _first_text(context: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = context.get(key)
        if isinstance(value, str):
            value = value.strip()
            if value:
                return value
    return None


def _normalize_status(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return _words(value)


def _normalize_event_name(value: str) -> str:
    return _words(value).replace(" ", "")


def _normalize_field_name(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return _words(value).replace(" ", "")


def _words(value: str) -> str:
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    return re.sub(r"[^a-z0-9]+", " ", spaced.lower()).strip()


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
