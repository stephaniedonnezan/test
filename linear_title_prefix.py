"""Build Linear issue title updates for Cursor research automations."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {
    "status",
    "statusid",
    "status_id",
    "state",
    "stateid",
    "state_id",
    "workflowstate",
    "workflowstateid",
    "workflow_state",
    "workflow_state_id",
}
_DIRECT_STATUS_TRIGGERS = {
    "statuschange",
    "statuschanged",
    "status_change",
    "status_changed",
    "statechange",
    "statechanged",
    "workflowstatechange",
    "workflowstatechanged",
}
_UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issueupdate",
    "issue_update",
    "issueupdated",
    "issue_updated",
    "updated_issue",
    "updatedissue",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when an issue moves to the research status."""
    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_change_event(contexts):
        return None

    new_status = _new_status(contexts)
    if _normalize_text(new_status) != TARGET_STATUS:
        return None

    issue_id = _issue_id(contexts)
    title = _first_text(contexts, ("title", "name"))
    if not issue_id or not title:
        return None

    cleaned_title = title.strip()
    if cleaned_title.lower().startswith(PREFIX.lower()):
        prefixed_title = cleaned_title
    else:
        prefixed_title = f"{PREFIX}: {cleaned_title}"

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": prefixed_title,
    }


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Collect likely metadata and issue objects without losing outer trigger data."""
    contexts: list[Mapping[str, Any]] = []

    def visit(value: Any) -> None:
        if not isinstance(value, Mapping):
            return
        contexts.append(value)
        for key in ("automation_trigger_info", "triggerContext", "data", "issue"):
            child = value.get(key)
            if isinstance(child, Mapping):
                visit(child)

    visit(event)
    return contexts


def _is_status_change_event(contexts: Sequence[Mapping[str, Any]]) -> bool:
    trigger_values = []
    for context in contexts:
        for key in ("trigger", "action", "type", "webhookType", "webhook_type"):
            value = context.get(key)
            if _text(value):
                trigger_values.append(_normalize_identifier(str(value)))

    if any(value in _DIRECT_STATUS_TRIGGERS for value in trigger_values):
        return True

    if any(value in _UPDATE_TRIGGERS for value in trigger_values):
        return _has_status_change_marker(contexts)

    return False


def _has_status_change_marker(contexts: Sequence[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            if _contains_status_field(context.get(key)):
                return True
        for key in ("changes", "updatedFrom", "updated_from", "previousValues"):
            value = context.get(key)
            if isinstance(value, Mapping) and any(_is_status_field(name) for name in value):
                return True
    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)
    if isinstance(value, Mapping):
        names = (value.get("field"), value.get("name"), value.get("key"), value.get("id"))
        return any(_is_status_field(name) for name in names if name is not None)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return any(_contains_status_field(item) for item in value)
    return False


def _is_status_field(value: Any) -> bool:
    text = _text(value)
    return bool(text and _normalize_identifier(text) in _STATUS_FIELD_NAMES)


def _new_status(contexts: Sequence[Mapping[str, Any]]) -> str | None:
    explicit = _first_text(
        contexts,
        (
            "newStatus",
            "new_status",
            "statusName",
            "status_name",
            "newState",
            "new_state",
            "newWorkflowState",
            "new_workflow_state",
        ),
    )
    if explicit:
        return explicit

    changed = _status_from_changes(contexts)
    if changed:
        return changed

    return _first_named_text(contexts, ("status", "state", "workflowState", "workflow_state"))


def _status_from_changes(contexts: Sequence[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        changes = context.get("changes")
        if not isinstance(changes, Mapping):
            continue
        for field, value in changes.items():
            if _is_status_field(field):
                status = _changed_to_value(value)
                if status:
                    return status
    return None


def _changed_to_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("to", "new", "after", "value", "name"):
            text = _named_text(value.get(key))
            if text:
                return text
    return _named_text(value)


def _issue_id(contexts: Sequence[Mapping[str, Any]]) -> str | None:
    return _first_text(contexts, ("issueId", "issue_id", "identifier", "key")) or _first_text(
        list(reversed(contexts)), ("id",)
    )


def _first_text(contexts: Sequence[Mapping[str, Any]], keys: Sequence[str]) -> str | None:
    for context in contexts:
        for key in keys:
            text = _text(context.get(key))
            if text:
                return text
    return None


def _first_named_text(contexts: Sequence[Mapping[str, Any]], keys: Sequence[str]) -> str | None:
    for context in contexts:
        for key in keys:
            text = _named_text(context.get(key))
            if text:
                return text
    return None


def _named_text(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("name", "title", "displayName", "display_name"):
            text = _text(value.get(key))
            if text:
                return text
        return None
    return _text(value)


def _text(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _normalize_text(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[_\-\s]+", " ", text).strip().lower()
    return text


def _normalize_identifier(value: str) -> str:
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", value.strip())
    return re.sub(r"[\s\-]+", "_", text).lower()


def main() -> int:
    """Read a JSON event from stdin and print the computed action."""
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    result = build_issue_title_update(payload)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
