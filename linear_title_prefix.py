"""Build Linear issue-title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


RESEARCH_STATUS = "to research"
TITLE_PREFIX = "Cursor researching"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow state"}
STATUS_TRIGGER_TOKENS = {
    "statuschanged",
    "status changed",
    "statuschange",
    "statechanged",
    "state changed",
    "workflowstatechanged",
    "workflow state changed",
}
ISSUE_UPDATE_TOKENS = {
    "update",
    "updated",
    "issueupdate",
    "issue update",
    "issueupdated",
    "issue updated",
    "updatedissue",
    "updated issue",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to To Research."""

    if not isinstance(event, Mapping):
        return None

    context = _event_context(event)
    if not _is_status_change(context):
        return None

    if _normalize_status(_status_value(context)) != RESEARCH_STATUS:
        return None

    issue_id = _string_value(context, ("issueId", "issue_id", "id", "identifier", "key"))
    title = _string_value(context, ("title", "name"))
    if issue_id is None or title is None:
        return None

    if title.lower().startswith(TITLE_PREFIX.lower()):
        prefixed_title = title
    else:
        prefixed_title = f"{TITLE_PREFIX}: {title}"

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": prefixed_title,
    }


def _event_context(event: Mapping[str, Any]) -> dict[str, Any]:
    context: dict[str, Any] = {}

    def merge(value: Any) -> None:
        if isinstance(value, Mapping):
            context.update(value)

    trigger_context = event.get("triggerContext")
    data = event.get("data")
    issue = data.get("issue") if isinstance(data, Mapping) else None

    merge(issue)
    merge(data)
    merge(trigger_context)
    merge(event)

    if isinstance(issue, Mapping):
        state = issue.get("state")
        if isinstance(state, Mapping) and "status" not in context:
            context["status"] = state.get("name")
        workflow_state = issue.get("workflowState")
        if isinstance(workflow_state, Mapping) and "workflowState" not in context:
            context["workflowState"] = workflow_state.get("name")

    return context


def _is_status_change(context: Mapping[str, Any]) -> bool:
    trigger_values = [
        context.get("trigger"),
        context.get("webhookType"),
        context.get("action"),
        context.get("type"),
    ]
    normalized_triggers = {_normalize_token(value) for value in trigger_values if value is not None}

    if normalized_triggers & STATUS_TRIGGER_TOKENS:
        return True

    if normalized_triggers & ISSUE_UPDATE_TOKENS:
        return _updated_status_fields(context)

    return False


def _updated_status_fields(context: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        if _contains_status_field(context.get(key)):
            return True

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        return any(_normalize_field_name(key) in STATUS_FIELDS for key in changes)

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_field_name(value) in STATUS_FIELDS

    if isinstance(value, Mapping):
        return any(_normalize_field_name(key) in STATUS_FIELDS for key in value)

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return any(_contains_status_field(item) for item in value)

    return False


def _status_value(context: Mapping[str, Any]) -> Any:
    for key in ("newStatus", "new_status", "status", "state", "workflowState"):
        value = context.get(key)
        if isinstance(value, Mapping):
            for nested_key in ("name", "title", "status"):
                nested_value = value.get(nested_key)
                if nested_value is not None:
                    return nested_value
        elif value is not None:
            return value

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        for key in ("status", "state", "workflowState"):
            value = changes.get(key)
            if isinstance(value, Mapping):
                for nested_key in ("newValue", "new_value", "to", "name"):
                    nested_value = value.get(nested_key)
                    if nested_value is not None:
                        return nested_value
            elif value is not None:
                return value

    return None


def _string_value(context: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = context.get(key)
        if isinstance(value, str):
            stripped = value.strip()
            if stripped:
                return stripped
    return None


def _normalize_status(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return _normalize_token(value)


def _normalize_token(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return re.sub(r"[\s_-]+", " ", separated).strip().lower()


def _normalize_field_name(value: Any) -> str:
    return _normalize_token(value).replace(" ", "")


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
