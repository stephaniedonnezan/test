"""Build Linear issue title update actions for research-status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"
STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflowstate",
    "workflowstatus",
}
STATUS_CHANGE_TRIGGERS = {
    "statuschange",
    "statuschanged",
    "statusupdated",
    "statechange",
    "statechanged",
    "workflowstatechange",
    "workflowstatechanged",
}
ISSUE_UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issueupdate",
    "issueupdated",
    "updatedissue",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue enters research."""

    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_change_event(contexts):
        return None

    status = _status_name(contexts)
    if _normalize_token(status) != _normalize_token(RESEARCH_STATUS):
        return None

    issue_id = _first_text(contexts, "issueId", "issue_id", "identifier", "id")
    title = _first_text(contexts, "title")
    if issue_id is None or title is None:
        return None

    clean_title = title.strip()
    if not clean_title or clean_title.lower().startswith(TITLE_PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {clean_title}",
    }


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return likely Linear payload layers from most to least specific."""

    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)

    trigger_context = event.get("triggerContext")
    data = event.get("data")
    issue = event.get("issue")

    add(trigger_context)
    if isinstance(trigger_context, Mapping):
        add(trigger_context.get("issue"))
        add(trigger_context.get("data"))

    if isinstance(data, Mapping):
        add(data.get("issue"))
    add(data)
    add(issue)
    add(event)
    return contexts


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    trigger_values = []
    for context in contexts:
        for key in ("trigger", "webhookType", "action", "type"):
            value = _text_value(context.get(key))
            if value is not None:
                trigger_values.append(_normalize_token(value))

    if any(value in STATUS_CHANGE_TRIGGERS for value in trigger_values):
        return True

    if not any(value in ISSUE_UPDATE_TRIGGERS for value in trigger_values):
        return False

    updated_fields = _updated_fields(contexts)
    return any(field in STATUS_FIELD_NAMES for field in updated_fields)


def _updated_fields(contexts: list[Mapping[str, Any]]) -> set[str]:
    fields: set[str] = set()
    for context in contexts:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            value = context.get(key)
            if isinstance(value, str):
                fields.add(_normalize_token(value))
            elif isinstance(value, list | tuple | set):
                fields.update(_normalize_token(item) for item in value if isinstance(item, str))
    return fields


def _status_name(contexts: list[Mapping[str, Any]]) -> str | None:
    explicit_status = _first_text(contexts, "newStatus", "new_status", "newState", "new_state")
    if explicit_status is not None:
        return explicit_status

    return _first_text(contexts, "status", "state", "workflowState", "workflow_state")


def _first_text(contexts: list[Mapping[str, Any]], *keys: str) -> str | None:
    for context in contexts:
        for key in keys:
            value = _text_value(context.get(key))
            if value is not None and value.strip():
                return value
    return None


def _text_value(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        name = value.get("name")
        if isinstance(name, str):
            return name
    return None


def _normalize_token(value: str | None) -> str:
    if value is None:
        return ""

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return re.sub(r"[^a-z0-9]+", "", spaced.lower())


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        json.dump(action, sys.stdout)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
