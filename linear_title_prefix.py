"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflowstate",
    "statusid",
    "stateid",
    "workflowstateid",
}
DIRECT_STATUS_CHANGE_TRIGGERS = {
    "statuschanged",
    "statuschange",
    "statechanged",
    "statechange",
    "workflowstatechanged",
    "workflowstatechange",
}
GENERIC_UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issueupdate",
    "issueupdated",
    "issue update",
    "issue updated",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update action when an issue moves to "to research".

    The function is intentionally side-effect free. Automation runners can use the
    returned action to call the Linear update API, while tests can exercise the
    payload parsing without network access.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _collect_contexts(event)
    if not _is_status_change_event(contexts):
        return None

    status = _new_status(contexts)
    if _normalize_status(status) != _normalize_status(TARGET_STATUS):
        return None

    issue_id = _first_text(contexts, ("issueId", "issue_id", "id", "identifier", "key"))
    title = _first_text(contexts, ("title", "name"))
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


def _collect_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Collect likely Linear/Cursor context objects from outermost to innermost."""

    contexts: list[Mapping[str, Any]] = []

    def visit(value: Any) -> None:
        if not isinstance(value, Mapping) or value in contexts:
            return

        contexts.append(value)
        for key in (
            "automation_trigger_info",
            "automationTriggerInfo",
            "triggerContext",
            "trigger_context",
            "payload",
            "data",
            "issue",
        ):
            nested = value.get(key)
            if isinstance(nested, Mapping):
                visit(nested)

    visit(event)
    return contexts


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    trigger_values = [
        _normalize_trigger(value)
        for context in contexts
        for key in ("trigger", "webhookType", "webhook_type", "action", "type", "event")
        for value in (context.get(key),)
        if isinstance(value, str)
    ]

    if any(value in DIRECT_STATUS_CHANGE_TRIGGERS for value in trigger_values):
        return True

    if any(value in GENERIC_UPDATE_TRIGGERS for value in trigger_values):
        return _has_status_changed_field(contexts)

    return False


def _has_status_changed_field(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            if _contains_status_field(context.get(key)):
                return True

        for key in ("changes", "changed", "updatedFrom", "updated_from"):
            changes = context.get(key)
            if isinstance(changes, Mapping) and any(_is_status_field(name) for name in changes):
                return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)

    if isinstance(value, Mapping):
        return any(_is_status_field(key) or _contains_status_field(item) for key, item in value.items())

    if isinstance(value, list | tuple | set):
        return any(_contains_status_field(item) for item in value)

    return False


def _is_status_field(value: Any) -> bool:
    if not isinstance(value, str):
        return False

    return _normalize_field_name(value) in STATUS_FIELD_NAMES


def _new_status(contexts: list[Mapping[str, Any]]) -> Any:
    changed_status = _changed_status_value(contexts)
    if changed_status is not None:
        return changed_status

    for context in contexts:
        for key in (
            "newStatus",
            "new_status",
            "newState",
            "new_state",
            "toStatus",
            "to_status",
            "statusName",
            "status_name",
        ):
            status = _status_text(context.get(key))
            if status is not None:
                return status

    for context in contexts:
        for key in ("status", "state", "workflowState", "workflow_state"):
            status = _status_text(context.get(key))
            if status is not None:
                return status

    return None


def _changed_status_value(contexts: list[Mapping[str, Any]]) -> Any:
    for context in contexts:
        for key in ("changes", "changed"):
            status = _status_from_change_map(context.get(key), prefer_new=True)
            if status is not None:
                return status

        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            status = _status_from_changed_fields(context.get(key))
            if status is not None:
                return status

    return None


def _status_from_change_map(value: Any, prefer_new: bool) -> str | None:
    if not isinstance(value, Mapping):
        return None

    for field_name, change in value.items():
        if not _is_status_field(field_name):
            continue

        if prefer_new and isinstance(change, Mapping):
            for key in ("to", "new", "newValue", "new_value", "after", "current", "name"):
                status = _status_text(change.get(key))
                if status is not None:
                    return status

        status = _status_text(change)
        if status is not None:
            return status

    return None


def _status_from_changed_fields(value: Any) -> str | None:
    if isinstance(value, Mapping):
        direct_status = _status_from_change_map(value, prefer_new=True)
        if direct_status is not None:
            return direct_status

        for field_name, change in value.items():
            if _is_status_field(field_name):
                status = _status_text(change)
                if status is not None:
                    return status

    if isinstance(value, list | tuple | set):
        for item in value:
            if isinstance(item, Mapping):
                field_name = item.get("field") or item.get("name") or item.get("key")
                if not _is_status_field(field_name):
                    continue

                for key in ("to", "new", "newValue", "new_value", "after", "value"):
                    status = _status_text(item.get(key))
                    if status is not None:
                        return status

    return None


def _status_text(value: Any) -> str | None:
    if isinstance(value, str):
        return value

    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            nested = value.get(key)
            if isinstance(nested, str):
                return nested

    return None


def _first_text(contexts: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for context in reversed(contexts):
        for key in keys:
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value

    return None


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def _normalize_status(value: Any) -> str | None:
    if value is None:
        return None

    status = _status_text(value)
    if status is None:
        return None

    status = _split_camel_case(status)
    status = re.sub(r"[^a-z0-9]+", " ", status.lower())
    return " ".join(status.split())


def _normalize_trigger(value: str) -> str:
    normalized = _split_camel_case(value)
    normalized = re.sub(r"[^a-z0-9]+", "", normalized.lower())
    return normalized


def _normalize_field_name(value: str) -> str:
    normalized = _split_camel_case(value)
    normalized = re.sub(r"[^a-z0-9]+", "", normalized.lower())
    return normalized


def _split_camel_case(value: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)


def main() -> int:
    event = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(event), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
