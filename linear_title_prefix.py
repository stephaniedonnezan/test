"""Build Linear issue title updates for research-status automations."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {"status", "state", "workflowstate"}
_DIRECT_STATUS_CHANGE_EVENTS = {
    "statuschange",
    "statuschanged",
    "statechange",
    "statechanged",
    "workflowstatechange",
    "workflowstatechanged",
}
_GENERIC_UPDATE_EVENTS = {"update", "updated", "issueupdate", "issueupdated", "updatedissue"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to To Research.

    The Cursor automation payload can arrive as a flat ``triggerContext`` object,
    while Linear webhooks commonly nest issue data under ``data.issue``. This
    function accepts both shapes and returns a side-effect-free action that the
    caller can apply to Linear.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    status = _extract_new_status(event)
    if _normalize_words(status) != TARGET_STATUS:
        return None

    issue_id = _extract_text(event, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _extract_text(event, ("title", "name"))
    if not issue_id or not title:
        return None

    clean_title = title.strip()
    if clean_title.casefold().startswith(PREFIX.casefold()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {clean_title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    trigger_values = list(_extract_trigger_values(event))
    for trigger_value in trigger_values:
        compact = _normalize_compact(trigger_value)
        if compact in _DIRECT_STATUS_CHANGE_EVENTS:
            return True

    has_generic_update_trigger = any(
        _normalize_compact(trigger_value) in _GENERIC_UPDATE_EVENTS
        for trigger_value in trigger_values
    )
    return has_generic_update_trigger and _updated_fields_include_status(event)


def _extract_new_status(event: Mapping[str, Any]) -> str | None:
    explicit_status_keys = (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "newWorkflowState",
        "new_workflow_state",
        "toStatus",
        "to_status",
        "toState",
        "to_state",
    )
    for context in _contexts(event):
        status = _first_named_value(context, explicit_status_keys)
        if status:
            return status

    status_from_changes = _status_from_changes(event)
    if status_from_changes:
        return status_from_changes

    for context in _contexts(event):
        status = _first_named_value(context, ("status", "state", "workflowState", "workflow_state"))
        if status:
            return status

    return None


def _extract_text(event: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for context in _issue_contexts(event):
        value = _first_named_value(context, keys)
        if value:
            return value
    return None


def _extract_trigger_values(event: Mapping[str, Any]) -> Iterable[str]:
    trigger_keys = ("trigger", "triggerType", "trigger_type", "webhookType", "webhook_type", "action", "type")
    for context in _contexts(event):
        for key in trigger_keys:
            value = context.get(key)
            text = _value_text(value)
            if text:
                yield text


def _updated_fields_include_status(event: Mapping[str, Any]) -> bool:
    field_keys = ("updatedFields", "updated_fields", "changedFields", "changed_fields")
    for context in _contexts(event):
        for key in field_keys:
            fields = context.get(key)
            if fields and _contains_status_field(fields):
                return True

        changes = context.get("changes")
        if isinstance(changes, Mapping) and any(_is_status_field_name(str(key)) for key in changes):
            return True

    return False


def _status_from_changes(event: Mapping[str, Any]) -> str | None:
    new_value_keys = ("newValue", "new_value", "new", "to", "after", "current")
    for context in _contexts(event):
        changes = context.get("changes")
        if not isinstance(changes, Mapping):
            continue

        for key, change in changes.items():
            if not _is_status_field_name(str(key)):
                continue
            if isinstance(change, Mapping):
                status = _first_named_value(change, new_value_keys)
                if status:
                    return status
            else:
                status = _value_text(change)
                if status:
                    return status

    return None


def _contains_status_field(fields: Any) -> bool:
    if isinstance(fields, str):
        return _is_status_field_name(fields)

    if isinstance(fields, Mapping):
        return any(_is_status_field_name(str(key)) for key in fields)

    if isinstance(fields, Iterable):
        return any(_is_status_field_name(str(field)) for field in fields)

    return False


def _is_status_field_name(name: str) -> bool:
    return _normalize_compact(name) in _STATUS_FIELD_NAMES


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)

    add(event)
    add(event.get("triggerContext"))
    add(event.get("data"))
    add(event.get("issue"))

    data = event.get("data")
    if isinstance(data, Mapping):
        add(data.get("issue"))
        add(data.get("node"))

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        add(trigger_context.get("issue"))

    return contexts


def _issue_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)

    add(event.get("triggerContext"))

    data = event.get("data")
    if isinstance(data, Mapping):
        add(data.get("issue"))
        add(data.get("node"))
        add(data)

    add(event.get("issue"))
    add(event)
    return contexts


def _first_named_value(context: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = context.get(key)
        text = _value_text(value)
        if text:
            return text
    return None


def _value_text(value: Any) -> str | None:
    if value is None:
        return None

    if isinstance(value, Mapping):
        return _first_named_value(value, ("name", "title", "label", "id", "identifier", "key"))

    if isinstance(value, (str, int, float)):
        text = str(value).strip()
        return text or None

    return None


def _normalize_words(value: Any) -> str:
    text = _value_text(value)
    if not text:
        return ""

    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.casefold().split())


def _normalize_compact(value: Any) -> str:
    return _normalize_words(value).replace(" ", "")


def main() -> int:
    event = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(event), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
