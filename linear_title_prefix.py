"""Build Linear issue title updates for research status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"
STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflow state",
    "state id",
    "status id",
    "workflow state id",
}
DIRECT_STATUS_CHANGE_EVENTS = {
    "status changed",
    "status change",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
}
GENERIC_UPDATE_EVENTS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return the title update action for Linear issues moved to research."""
    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    if _normalize(_new_status(event)) != RESEARCH_STATUS:
        return None

    issue_id = _string_value(_first_context_value(event, ("issueId", "issue_id", "identifier", "key", "id")))
    title = _string_value(_first_context_value(event, ("title", "name")))
    if issue_id is None or title is None:
        return None

    title = title.strip()
    if not title or _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    event_names = {
        _normalize(value)
        for context in _contexts(event)
        for key in ("trigger", "webhookType", "webhook_type", "action", "type", "eventType", "event_type")
        if (value := context.get(key)) is not None
    }

    if event_names & DIRECT_STATUS_CHANGE_EVENTS:
        return True

    if event_names & GENERIC_UPDATE_EVENTS:
        return _status_field_changed(event)

    return _status_field_changed(event)


def _status_field_changed(event: Mapping[str, Any]) -> bool:
    for context in _contexts(event):
        updated_fields = context.get("updatedFields") or context.get("updated_fields")
        if _contains_status_field(updated_fields):
            return True

        for key in ("updatedFrom", "updated_from", "changes", "changedFields", "changed_fields"):
            changed = context.get(key)
            if isinstance(changed, Mapping) and _contains_status_field(changed.keys()):
                return True
            if _contains_status_field(changed):
                return True

    return False


def _contains_status_field(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return _normalize(value) in STATUS_FIELD_NAMES
    if isinstance(value, Mapping):
        return any(_contains_status_field(key) for key in value)
    if isinstance(value, list | tuple | set):
        return any(_contains_status_field(item) for item in value)
    return False


def _new_status(event: Mapping[str, Any]) -> Any:
    explicit = _first_context_value(
        event,
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

    changed_status = _new_status_from_changes(event)
    if changed_status is not None:
        return changed_status

    return _first_context_value(event, ("status", "state", "workflowState", "workflow_state"))


def _new_status_from_changes(event: Mapping[str, Any]) -> Any:
    for context in _contexts(event):
        changes = context.get("changes") or context.get("changedFields") or context.get("changed_fields")
        if not isinstance(changes, Mapping):
            continue

        for field_name, change in changes.items():
            if _normalize(field_name) not in STATUS_FIELD_NAMES:
                continue
            if isinstance(change, Mapping):
                for key in ("new", "newValue", "new_value", "to", "after", "value"):
                    if key in change:
                        return change[key]
            else:
                return change

    return None


def _first_context_value(event: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    for context in _contexts(event):
        for key in keys:
            if key in context and context[key] is not None:
                value = _status_name(context[key])
                if value is not None:
                    return value
    return None


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)

    trigger_context = event.get("triggerContext") or event.get("trigger_context")
    add(trigger_context)
    if isinstance(trigger_context, Mapping):
        data = trigger_context.get("data")
        issue = trigger_context.get("issue")
        add(issue)
        add(data)
        if isinstance(data, Mapping):
            add(data.get("issue"))

    data = event.get("data")
    issue = event.get("issue")
    add(issue)
    add(data)
    if isinstance(data, Mapping):
        add(data.get("issue"))

    add(event)
    return contexts


def _status_name(value: Any) -> Any:
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            if key in value:
                return value[key]
    return value


def _string_value(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    if isinstance(value, int):
        return str(value)
    return None


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def _normalize(value: Any) -> str:
    text = _string_value(_status_name(value))
    if text is None:
        return ""
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
