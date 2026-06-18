"""Build Linear issue title updates for research status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "workflow state", "workflowstate"}
DIRECT_STATUS_TRIGGERS = {
    "status changed",
    "status change",
    "issue status changed",
    "issue status change",
}
GENERIC_UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to To Research."""

    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_change_event(contexts):
        return None

    new_status = _new_status(contexts)
    if _normalize(new_status) != TARGET_STATUS:
        return None

    issue_contexts = _issue_contexts(event)
    issue_id = _first_text(issue_contexts, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_text(issue_contexts, ("title", "name"))
    if not issue_id or not title:
        return None

    if title.lower().startswith(TITLE_PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return payload mappings from outermost to innermost trigger context."""

    contexts: list[Mapping[str, Any]] = [event]
    for key in ("triggerContext", "webhook", "payload", "data", "issue"):
        value = event.get(key)
        if isinstance(value, Mapping):
            contexts.append(value)

    data = event.get("data")
    if isinstance(data, Mapping):
        for key in ("issue", "node"):
            value = data.get(key)
            if isinstance(value, Mapping):
                contexts.append(value)

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        data = trigger_context.get("data")
        if isinstance(data, Mapping):
            contexts.append(data)

    return contexts


def _issue_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return likely issue mappings before automation wrapper metadata."""

    contexts: list[Mapping[str, Any]] = []

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        contexts.append(trigger_context)

    data = event.get("data")
    if isinstance(data, Mapping):
        for key in ("issue", "node"):
            value = data.get(key)
            if isinstance(value, Mapping):
                contexts.append(value)
        contexts.append(data)

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        contexts.append(issue)

    contexts.append(event)
    return contexts


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    trigger_values = []
    for context in contexts:
        for key in ("trigger", "webhookType", "webhook_type", "action", "type", "eventType"):
            value = _text(context.get(key))
            if value:
                trigger_values.append(_normalize(value))

    if any(value in DIRECT_STATUS_TRIGGERS for value in trigger_values):
        return True

    if any(value in GENERIC_UPDATE_TRIGGERS for value in trigger_values):
        return _changed_fields_include_status(contexts)

    return False


def _changed_fields_include_status(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            value = context.get(key)
            if _field_collection_includes_status(value):
                return True

        changes = context.get("changes")
        if isinstance(changes, Mapping) and any(_is_status_field(key) for key in changes):
            return True

    return False


def _field_collection_includes_status(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)

    if isinstance(value, Mapping):
        return any(_is_status_field(key) for key in value)

    if isinstance(value, (list, tuple, set)):
        for item in value:
            if isinstance(item, Mapping):
                field_name = _first_text((item,), ("field", "fieldName", "name", "key"))
                if field_name and _is_status_field(field_name):
                    return True
            elif _is_status_field(item):
                return True

    return False


def _is_status_field(value: Any) -> bool:
    normalized = _normalize(value)
    return normalized in STATUS_FIELD_NAMES


def _new_status(contexts: list[Mapping[str, Any]]) -> str | None:
    explicit_keys = (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "newWorkflowState",
        "new_workflow_state",
        "statusName",
        "stateName",
        "workflowStateName",
    )
    for context in contexts:
        status = _first_status_text(context, explicit_keys)
        if status:
            return status

    status_from_changes = _status_from_changes(contexts)
    if status_from_changes:
        return status_from_changes

    fallback_keys = ("status", "state", "workflowState", "workflow_state")
    for context in contexts:
        status = _first_status_text(context, fallback_keys)
        if status:
            return status

    return None


def _status_from_changes(contexts: list[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        changes = context.get("changes")
        if not isinstance(changes, Mapping):
            continue

        for field_name, change in changes.items():
            if not _is_status_field(field_name):
                continue

            status = _first_status_text(
                change,
                ("to", "after", "new", "value", "newValue", "new_value", "name"),
            )
            if status:
                return status

    return None


def _first_status_text(context: Any, keys: tuple[str, ...]) -> str | None:
    if not isinstance(context, Mapping):
        return _text(context)

    for key in keys:
        if key in context:
            value = context[key]
            text = _text(value)
            if text:
                return text

            if isinstance(value, Mapping):
                nested = _first_text((value,), ("name", "title", "label"))
                if nested:
                    return nested

    return None


def _first_text(
    contexts: tuple[Mapping[str, Any], ...] | list[Mapping[str, Any]],
    keys: tuple[str, ...],
) -> str | None:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            text = _text(value)
            if text:
                return text
    return None


def _text(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            text = _text(value.get(key))
            if text:
                return text

    return None


def _normalize(value: Any) -> str:
    text = _text(value)
    if not text:
        return ""

    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def main() -> int:
    event = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(event), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
