"""Build Linear issue title updates for research status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "workflow state", "workflowstate"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue-title update action when an issue moves to To Research."""

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    new_status = _new_status(event)
    if _normalize(new_status) != TARGET_STATUS:
        return None

    issue_id = _first_text(event, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_text(event, ("title",))
    if not issue_id or not title:
        return None

    title = title.strip()
    if title.casefold().startswith(TITLE_PREFIX.casefold()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    trigger_values = [
        value
        for context in _metadata_contexts(event)
        for key, value in context.items()
        if _normalize(key)
        in {"trigger", "webhook type", "webhooktype", "action", "type", "event", "event type"}
    ]

    if any(_is_direct_status_change(value) for value in trigger_values):
        return True

    if any(_is_issue_update(value) for value in trigger_values):
        return _mentions_status_field(event)

    return False


def _new_status(event: Mapping[str, Any]) -> str | None:
    explicit_status_keys = (
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
    fallback_status_keys = ("status", "state", "workflowState", "workflow_state")

    for context in _metadata_contexts(event):
        value = _value_for_any_key(context, explicit_status_keys)
        text = _text_from_status_value(value)
        if text:
            return text

    changed_value = _changed_status_value(event)
    if changed_value:
        return changed_value

    for context in _issue_contexts(event):
        value = _value_for_any_key(context, fallback_status_keys)
        text = _text_from_status_value(value)
        if text:
            return text

    for context in _metadata_contexts(event):
        value = _value_for_any_key(context, fallback_status_keys)
        text = _text_from_status_value(value)
        if text:
            return text

    return None


def _first_text(event: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for context in _issue_contexts(event):
        value = _value_for_any_key(context, keys)
        text = _text_from_status_value(value)
        if text:
            return text
    return None


def _issue_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []

    trigger_context = _mapping_at(event, "triggerContext")
    if trigger_context:
        contexts.append(trigger_context)

    direct_issue = _mapping_at(event, "issue")
    if direct_issue:
        contexts.append(direct_issue)

    data = _mapping_at(event, "data")
    data_issue = _mapping_at(data, "issue") if data else None
    if data_issue:
        contexts.append(data_issue)
    if data:
        contexts.append(data)

    contexts.append(event)
    return contexts


def _metadata_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = [event]

    trigger_context = _mapping_at(event, "triggerContext")
    if trigger_context:
        contexts.append(trigger_context)

    data = _mapping_at(event, "data")
    if data:
        contexts.append(data)

    return contexts


def _mapping_at(mapping: Mapping[str, Any] | None, key: str) -> Mapping[str, Any] | None:
    if not isinstance(mapping, Mapping):
        return None
    value = mapping.get(key)
    return value if isinstance(value, Mapping) else None


def _value_for_any_key(mapping: Mapping[str, Any], keys: Iterable[str]) -> Any:
    normalized_items = [(_normalize(key), value) for key, value in mapping.items()]
    for wanted_key in (_normalize(key) for key in keys):
        for actual_key, value in normalized_items:
            if actual_key == wanted_key:
                return value
    return None


def _changed_status_value(event: Mapping[str, Any]) -> str | None:
    for context in _metadata_contexts(event):
        for key in ("changes", "change", "updatedFields", "updated_fields"):
            value = _value_for_any_key(context, (key,))
            text = _changed_status_value_from(value)
            if text:
                return text
    return None


def _changed_status_value_from(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for field_name, field_change in value.items():
            if _normalize(field_name) in STATUS_FIELD_NAMES:
                text = _new_value_from_change(field_change)
                if text:
                    return text

        for key in ("newValue", "new_value", "to", "after", "name"):
            text = _text_from_status_value(_value_for_any_key(value, (key,)))
            if text:
                return text

    if isinstance(value, list):
        for item in value:
            if isinstance(item, Mapping):
                field_name = _value_for_any_key(item, ("field", "fieldName", "name", "key"))
                if field_name and _normalize(field_name) in STATUS_FIELD_NAMES:
                    text = _new_value_from_change(item)
                    if text:
                        return text

    return None


def _new_value_from_change(change: Any) -> str | None:
    if isinstance(change, Mapping):
        for key in ("newValue", "new_value", "to", "after", "value", "name"):
            text = _text_from_status_value(_value_for_any_key(change, (key,)))
            if text:
                return text
    return _text_from_status_value(change)


def _mentions_status_field(event: Mapping[str, Any]) -> bool:
    for context in _metadata_contexts(event):
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            value = _value_for_any_key(context, (key,))
            if _field_collection_mentions_status(value):
                return True

        changes = _value_for_any_key(context, ("changes", "change"))
        if _field_collection_mentions_status(changes):
            return True

    return False


def _field_collection_mentions_status(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize(value) in STATUS_FIELD_NAMES

    if isinstance(value, Mapping):
        if any(_normalize(key) in STATUS_FIELD_NAMES for key in value):
            return True
        field_name = _value_for_any_key(value, ("field", "fieldName", "name", "key"))
        return bool(field_name and _normalize(field_name) in STATUS_FIELD_NAMES)

    if isinstance(value, Iterable):
        return any(_field_collection_mentions_status(item) for item in value)

    return False


def _text_from_status_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        return text or None
    if isinstance(value, Mapping):
        for key in ("name", "title", "label", "value", "identifier", "id"):
            text = _text_from_status_value(_value_for_any_key(value, (key,)))
            if text:
                return text
    return None


def _is_direct_status_change(value: Any) -> bool:
    normalized = _normalize(value)
    if not normalized:
        return False
    return (
        ("status" in normalized or "state" in normalized)
        and ("changed" in normalized or "change" in normalized)
    )


def _is_issue_update(value: Any) -> bool:
    normalized = _normalize(value)
    return normalized in {"update", "updated", "issue update", "issue updated", "updated issue"}


def _normalize(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[_\-/]+", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().casefold()


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
