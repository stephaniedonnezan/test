"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"


def build_issue_title_update(event: Any) -> dict[str, str] | None:
    """Return a title update action when an issue moves to "to research"."""
    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    if _normalize_status(_new_status(event)) != TARGET_STATUS:
        return None

    issue_id = _string_value(_first_value(event, ("id", "issueId", "issue_id", "identifier")))
    title = _string_value(_first_value(event, ("title", "name")))
    if not issue_id or not title:
        return None

    if title.casefold().startswith(PREFIX.casefold()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    for context in _event_contexts(event):
        for key in ("trigger", "webhookType"):
            if _normalize_status(context.get(key)) == "status changed":
                return True

    update_actions = {"update", "updated", "issue updated", "updated issue"}
    for context in _event_contexts(event):
        action = _normalize_status(context.get("action") or context.get("type"))
        if action in update_actions and _changed_status_fields(context):
            return True

    return False


def _changed_status_fields(context: Mapping[str, Any]) -> set[str]:
    raw_fields = (
        context.get("updatedFields")
        or context.get("changedFields")
        or context.get("updated_fields")
        or context.get("changed_fields")
    )
    if isinstance(raw_fields, str):
        fields = [raw_fields]
    elif isinstance(raw_fields, Mapping):
        fields = raw_fields.keys()
    elif isinstance(raw_fields, list | tuple | set):
        fields = raw_fields
    else:
        fields = ()

    return {
        _normalize_status(field)
        for field in fields
        if _normalize_status(field) in {"status", "state", "workflow state"}
    }


def _new_status(event: Mapping[str, Any]) -> Any:
    explicit_status_keys = (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "newWorkflowState",
        "new_workflow_state",
    )
    explicit_status = _first_value(event, explicit_status_keys)
    if explicit_status is not None:
        return explicit_status

    for context in _event_contexts(event):
        for key in ("status", "state", "workflowState", "workflow_state"):
            value = context.get(key)
            if isinstance(value, Mapping):
                name = value.get("name")
                if name is not None:
                    return name
            elif value is not None:
                return value

    return None


def _first_value(event: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    for context in _event_contexts(event):
        for key in keys:
            value = context.get(key)
            if value is not None:
                return value
    return None


def _event_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return likely issue/trigger mappings in priority order."""
    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)

    add(event.get("triggerContext"))
    add(event.get("issue"))

    data = event.get("data")
    if isinstance(data, Mapping):
        add(data.get("issue"))
        add(data)

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        add(trigger_context.get("issue"))

    add(event)
    return contexts


def _normalize_status(value: Any) -> str:
    raw_value = _string_value(value)
    if not raw_value:
        return ""

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", raw_value)
    spaced = re.sub(r"[_\-/]+", " ", spaced)
    return re.sub(r"\s+", " ", spaced).strip().casefold()


def _string_value(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def main() -> int:
    payload = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(payload)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
