"""Build Linear issue title updates for research status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_TRIGGER_KEYS = ("trigger", "webhookType", "action", "type", "eventType")
_DIRECT_STATUS_CHANGE_TRIGGERS = {
    "status changed",
    "state changed",
    "workflow state changed",
}
_GENERIC_UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}
_STATUS_FIELD_NAMES = {
    "status",
    "status id",
    "state",
    "state id",
    "workflow state",
    "workflow state id",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title-update action when an issue moves to "to research".

    The function accepts both Cursor automation trigger contexts and common
    Linear webhook payloads. It is intentionally side-effect free so callers can
    decide how to apply the returned action.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    status = _extract_new_status(event)
    if _normalize(status) != TARGET_STATUS:
        return None

    issue_id = _extract_first_text(event, ("issueId", "issue_id", "id", "identifier", "key"))
    title = _extract_first_text(event, ("title", "name"))
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
    trigger_values = {_normalize(value) for value in _iter_trigger_values(event)}

    if trigger_values & _DIRECT_STATUS_CHANGE_TRIGGERS:
        return True

    if trigger_values & _GENERIC_UPDATE_TRIGGERS:
        return _updated_fields_include_status(event)

    return False


def _iter_trigger_values(event: Mapping[str, Any]) -> Iterable[Any]:
    for context in _contexts(event):
        for key in _TRIGGER_KEYS:
            value = context.get(key)
            if _is_text(value):
                yield value


def _updated_fields_include_status(event: Mapping[str, Any]) -> bool:
    for context in _contexts(event):
        updated_fields = context.get("updatedFields")
        if _fields_include_status(updated_fields):
            return True

        for key in ("changedFields", "changed_fields"):
            changed_fields = context.get(key)
            if _fields_include_status(changed_fields):
                return True

        for key in ("changes", "changed", "updatedFrom", "updated_from"):
            changes = context.get(key)
            if isinstance(changes, Mapping) and _fields_include_status(changes.keys()):
                return True

        field_name = context.get("field") or context.get("fieldName") or context.get("field_name")
        if _normalize(field_name) in _STATUS_FIELD_NAMES:
            return True

    return False


def _fields_include_status(fields: Any) -> bool:
    if isinstance(fields, Mapping):
        values = fields.keys()
    elif isinstance(fields, Iterable) and not _is_text(fields):
        values = fields
    else:
        return False

    return any(_normalize(value) in _STATUS_FIELD_NAMES for value in values)


def _extract_new_status(event: Mapping[str, Any]) -> str | None:
    explicit_keys = (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "newWorkflowState",
        "new_workflow_state",
        "statusName",
        "status_name",
        "stateName",
        "state_name",
        "workflowStateName",
        "workflow_state_name",
        "toStatus",
        "to_status",
        "toState",
        "to_state",
    )
    status = _extract_first_text(event, explicit_keys)
    if status is not None:
        return status

    for context in _contexts(event):
        for key in ("status", "state", "workflowState", "workflow_state"):
            status = _text_or_name(context.get(key))
            if status is not None:
                return status

        changes = context.get("changes")
        if isinstance(changes, Mapping):
            for key in ("status", "state", "workflowState", "workflow_state"):
                status = _text_or_name(changes.get(key))
                if status is not None:
                    return status

    return None


def _extract_first_text(event: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for context in _contexts(event):
        for key in keys:
            value = context.get(key)
            text = _text_or_name(value)
            if text is not None:
                return text
    return None


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
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

    add(event)
    return contexts


def _text_or_name(value: Any) -> str | None:
    if _is_text(value):
        text = str(value).strip()
        return text or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            text = _text_or_name(value.get(key))
            if text is not None:
                return text

    return None


def _has_prefix(title: str) -> bool:
    return title.lstrip().casefold().startswith(PREFIX.casefold())


def _normalize(value: Any) -> str:
    if not _is_text(value):
        return ""

    text = str(value)
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.casefold().split())


def _is_text(value: Any) -> bool:
    return isinstance(value, (str, int, float)) and not isinstance(value, bool)


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        json.dump(update, sys.stdout)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
