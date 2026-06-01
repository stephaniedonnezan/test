"""Build Linear issue title updates for issues entering research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_CHANGE_EVENTS = {
    "status changed",
    "status change",
    "status updated",
    "state changed",
    "state change",
    "state updated",
    "workflow state changed",
    "workflow state updated",
}
ISSUE_UPDATE_EVENTS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}
STATUS_FIELD_NAMES = {
    "status",
    "state",
    "stateid",
    "statustype",
    "workflowstate",
    "workflowstateid",
}


def build_issue_title_update(event: Any) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to research."""

    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_change_event(contexts):
        return None

    status = _find_status(contexts)
    if _normalize_words(status) != TARGET_STATUS:
        return None

    issue_id = _find_issue_id(contexts)
    title = _find_title(contexts)
    if not issue_id or not title:
        return None

    title = title.strip()
    if not title or title.casefold().startswith(PREFIX.casefold()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return useful payload mappings in value-precedence order."""

    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)

    trigger_context = event.get("triggerContext")
    data = event.get("data")
    issue = event.get("issue")

    add(event)
    add(trigger_context)

    if isinstance(trigger_context, Mapping):
        add(trigger_context.get("data"))
        trigger_data = trigger_context.get("data")
        if isinstance(trigger_data, Mapping):
            add(trigger_data.get("issue"))
        add(trigger_context.get("issue"))

    add(data)
    if isinstance(data, Mapping):
        add(data.get("issue"))

    add(issue)
    return contexts


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("trigger", "webhookType", "action", "type"):
            value = _string_value(context.get(key))
            normalized = _normalize_words(value)
            if normalized in STATUS_CHANGE_EVENTS:
                return True

    return _has_issue_update_event(contexts) and _has_status_field_change(contexts)


def _has_issue_update_event(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("trigger", "webhookType", "action", "type"):
            normalized = _normalize_words(_string_value(context.get(key)))
            if normalized in ISSUE_UPDATE_EVENTS:
                return True
    return False


def _has_status_field_change(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            if _contains_status_field(context.get(key)):
                return True

        updated_from = context.get("updatedFrom") or context.get("updated_from")
        if isinstance(updated_from, Mapping):
            for changed_key in updated_from:
                if _is_status_field_name(str(changed_key)):
                    return True

        changes = context.get("changes")
        if isinstance(changes, Mapping):
            for changed_key in changes:
                if _is_status_field_name(str(changed_key)):
                    return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field_name(value)

    if isinstance(value, Mapping):
        return any(_is_status_field_name(str(key)) for key in value)

    if isinstance(value, (list, tuple, set)):
        for item in value:
            if isinstance(item, Mapping):
                field_name = item.get("field") or item.get("name") or item.get("key")
                if _is_status_field_name(_string_value(field_name)):
                    return True
            elif _is_status_field_name(_string_value(item)):
                return True

    return False


def _is_status_field_name(value: str) -> bool:
    compact = re.sub(r"[^a-z0-9]", "", value.casefold())
    return compact in STATUS_FIELD_NAMES


def _find_status(contexts: list[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        for key in (
            "newStatus",
            "new_status",
            "statusName",
            "status_name",
            "stateName",
            "state_name",
            "workflowStateName",
            "workflow_state_name",
        ):
            value = _string_value(context.get(key))
            if value:
                return value

    for context in contexts:
        for key in ("status", "state", "workflowState", "workflow_state"):
            value = _named_value(context.get(key))
            if value:
                return value

    return None


def _find_issue_id(contexts: list[Mapping[str, Any]]) -> str | None:
    issue_contexts = [context for context in contexts if _string_value(context.get("title"))]
    for context in issue_contexts + contexts:
        for key in ("issueId", "issue_id", "identifier", "id"):
            value = _string_value(context.get(key))
            if value:
                return value
    return None


def _find_title(contexts: list[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        value = _string_value(context.get("title"))
        if value:
            return value
    return None


def _named_value(value: Any) -> str | None:
    direct_value = _string_value(value)
    if direct_value:
        return direct_value

    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            named = _string_value(value.get(key))
            if named:
                return named

    return None


def _string_value(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None

    if isinstance(value, int):
        return str(value)

    return None


def _normalize_words(value: str | None) -> str | None:
    if value is None:
        return None

    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    words = re.sub(r"[^a-zA-Z0-9]+", " ", spaced).casefold().split()
    return " ".join(words) if words else None


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
