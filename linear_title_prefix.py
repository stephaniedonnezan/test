"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


PREFIX = "Cursor researching"
PREFIXED_TITLE_TEMPLATE = f"{PREFIX}: {{title}}"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {
    "new status",
    "new state",
    "new workflow state",
    "status",
    "state",
    "workflow state",
    "workflow status",
}

_TRIGGER_KEYS = (
    "trigger",
    "action",
    "type",
    "webhookType",
    "webhook_type",
    "eventType",
    "event_type",
)

_DIRECT_STATUS_TRIGGERS = {
    "status changed",
    "status change",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
}

_GENERIC_UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Mapping[str, Any] | Any) -> dict[str, str] | None:
    """Return an issue-title update action when a Linear issue moves to research."""

    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_change_event(contexts):
        return None

    status = _find_status(contexts)
    if _normalize(status) != TARGET_STATUS:
        return None

    issue_id = _find_first_text(contexts, ("issueId", "issue_id", "id", "identifier", "key"))
    title = _find_first_text(contexts, ("title", "name"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if not title or _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": PREFIXED_TITLE_TEMPLATE.format(title=title),
    }


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []
    seen: set[int] = set()

    def add(value: Any) -> None:
        if not isinstance(value, Mapping) or id(value) in seen:
            return
        seen.add(id(value))
        contexts.append(value)

        for key in ("triggerContext", "trigger_context", "data", "issue"):
            add(value.get(key))

        data = value.get("data")
        if isinstance(data, Mapping):
            add(data.get("issue"))

    add(event)
    return contexts


def _is_status_change_event(contexts: Sequence[Mapping[str, Any]]) -> bool:
    trigger_values = [
        _normalize(context[key])
        for context in contexts
        for key in _TRIGGER_KEYS
        if key in context
    ]

    if any(value in _DIRECT_STATUS_TRIGGERS for value in trigger_values):
        return True

    if any(value in _GENERIC_UPDATE_TRIGGERS for value in trigger_values):
        return _has_status_change_marker(contexts)

    return _has_status_change_marker(contexts)


def _has_status_change_marker(contexts: Sequence[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            if _contains_status_field(context.get(key)):
                return True

        for key in ("changes", "changed", "updatedFrom", "updated_from"):
            if _contains_status_field(_change_field_names(context.get(key))):
                return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)

    if isinstance(value, Mapping):
        return any(_is_status_field(key) for key in value)

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return any(_contains_status_field(item) for item in value)

    return False


def _change_field_names(value: Any) -> list[str]:
    if isinstance(value, Mapping):
        field_names: list[str] = []
        for key, nested_value in value.items():
            field_names.append(str(key))
            field_names.extend(_change_field_names(nested_value))
        return field_names

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        field_names = []
        for item in value:
            if isinstance(item, Mapping):
                for key in ("field", "name", "key"):
                    if key in item:
                        field_names.append(str(item[key]))
                field_names.extend(_change_field_names(item))
            else:
                field_names.append(str(item))
        return field_names

    if value is None:
        return []

    return [str(value)]


def _is_status_field(value: Any) -> bool:
    normalized = _normalize(value)
    return normalized in _STATUS_FIELD_NAMES or normalized.endswith(" status")


def _find_status(contexts: Sequence[Mapping[str, Any]]) -> str | None:
    explicit_status_keys = (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "newWorkflowState",
        "new_workflow_state",
        "newWorkflowStateName",
        "new_workflow_state_name",
        "statusName",
        "status_name",
        "stateName",
        "state_name",
        "workflowStateName",
        "workflow_state_name",
    )
    status_keys = (
        "status",
        "state",
        "workflowState",
        "workflow_state",
        "workflowStatus",
        "workflow_status",
    )

    for keys in (explicit_status_keys, status_keys):
        for context in contexts:
            value = _find_first_text((context,), keys)
            if value:
                return value

    return None


def _find_first_text(contexts: Sequence[Mapping[str, Any]], keys: Sequence[str]) -> str | None:
    for context in contexts:
        for key in keys:
            if key not in context:
                continue

            value = _text_value(context[key])
            if value:
                return value

    return None


def _text_value(value: Any) -> str | None:
    if isinstance(value, str):
        return value

    if isinstance(value, (int, float)):
        return str(value)

    if isinstance(value, Mapping):
        for key in ("name", "title", "label", "identifier", "key", "id"):
            nested = _text_value(value.get(key))
            if nested:
                return nested

    return None


def _has_research_prefix(title: str) -> bool:
    return re.match(r"^\s*cursor\s+researching\b", title, flags=re.IGNORECASE) is not None


def _normalize(value: Any) -> str:
    text = _text_value(value)
    if text is None:
        return ""

    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def main() -> int:
    """Read a JSON event from stdin and print the title update action or null."""

    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        print("null")
        return 1

    print(json.dumps(build_issue_title_update(event), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
