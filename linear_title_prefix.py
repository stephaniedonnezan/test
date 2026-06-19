"""Build Linear issue-title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflowstate",
    "workflow status",
    "workflow state",
    "workflow_state",
}
TRIGGER_KEYS = ("trigger", "webhookType", "webhook_type", "action", "type", "event")
DIRECT_STATUS_TRIGGERS = {
    "status changed",
    "status change",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
    "workflow status changed",
    "workflow status change",
}
GENERIC_UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Any) -> dict[str, str] | None:
    """Return an issue-title update action when a payload moves to To Research.

    The function accepts both flat Cursor automation trigger contexts and nested
    Linear webhook payloads. It returns ``None`` when the event is not a status
    change to To Research, when required issue data is missing, or when the title
    already has the research prefix.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _collect_contexts(event)
    if not contexts:
        return None

    if not _is_status_change_event(contexts):
        return None

    status = _extract_new_status(contexts)
    if _normalize_text(status) != TARGET_STATUS:
        return None

    issue_id = _extract_issue_id(contexts)
    title = _extract_title(contexts)
    if not issue_id or not title or _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _collect_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return likely metadata and issue-data mappings from outer to inner."""

    contexts: list[Mapping[str, Any]] = [event]

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        contexts.append(trigger_context)

    automation_info = event.get("automation_trigger_info")
    if isinstance(automation_info, Mapping):
        contexts.append(automation_info)
        nested_trigger_context = automation_info.get("triggerContext")
        if isinstance(nested_trigger_context, Mapping):
            contexts.append(nested_trigger_context)

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        contexts.append(issue)

    data = event.get("data")
    if isinstance(data, Mapping):
        contexts.append(data)
        data_issue = data.get("issue")
        if isinstance(data_issue, Mapping):
            contexts.append(data_issue)

    return contexts


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    trigger_values = [
        normalized
        for context in contexts
        for key in TRIGGER_KEYS
        if (normalized := _normalize_text(context.get(key)))
    ]

    if any(value in DIRECT_STATUS_TRIGGERS for value in trigger_values):
        return True

    if _has_changed_status_field(contexts):
        return True

    if not trigger_values:
        return False

    return False


def _has_changed_status_field(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            if _contains_status_field(context.get(key)):
                return True

        changes = context.get("changes") or context.get("changed")
        if isinstance(changes, Mapping):
            if any(_is_status_field_name(key) for key in changes):
                return True
        elif _contains_status_field(changes):
            return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field_name(value)

    if isinstance(value, Mapping):
        for key in ("field", "fieldName", "field_name", "name", "key", "property", "path"):
            if _is_status_field_name(value.get(key)):
                return True
        if any(_is_status_field_name(key) for key in value):
            return True
        return any(_contains_status_field(item) for item in value.values())

    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        return any(_contains_status_field(item) for item in value)

    return False


def _is_status_field_name(value: Any) -> bool:
    normalized = _normalize_text(value)
    return normalized in STATUS_FIELD_NAMES


def _extract_new_status(contexts: list[Mapping[str, Any]]) -> str | None:
    for status in _status_values_from_changes(contexts):
        if _is_candidate_status(status):
            return _string_value(status)

    for context in contexts:
        for key in (
            "newStatus",
            "new_status",
            "newState",
            "new_state",
            "status",
            "state",
            "workflowState",
            "workflow_state",
        ):
            status = _status_name_from_value(context.get(key))
            if _is_candidate_status(status):
                return _string_value(status)

    return None


def _status_values_from_changes(contexts: list[Mapping[str, Any]]) -> list[Any]:
    values: list[Any] = []
    for context in contexts:
        changes = context.get("changes") or context.get("changed")
        if isinstance(changes, Mapping):
            for field_name, change in changes.items():
                if _is_status_field_name(field_name):
                    values.extend(_new_values_from_change(change))

        for key in ("changedFields", "changed_fields", "updatedFields", "updated_fields"):
            changed_fields = context.get(key)
            if isinstance(changed_fields, Iterable) and not isinstance(changed_fields, (str, bytes, Mapping)):
                for item in changed_fields:
                    if isinstance(item, Mapping) and _contains_status_field(item):
                        values.extend(_new_values_from_change(item))
            elif isinstance(changed_fields, Mapping) and _contains_status_field(changed_fields):
                values.extend(_new_values_from_change(changed_fields))

    return values


def _new_values_from_change(change: Any) -> list[Any]:
    if not isinstance(change, Mapping):
        return [change]

    values: list[Any] = []
    for key in (
        "newValue",
        "new_value",
        "new",
        "to",
        "after",
        "value",
        "name",
    ):
        if key in change:
            values.append(_status_name_from_value(change.get(key)))

    return values


def _status_name_from_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        for key in ("name", "label", "title"):
            nested = value.get(key)
            if _string_value(nested):
                return nested
        return None
    return value


def _is_candidate_status(value: Any) -> bool:
    text = _string_value(value)
    if not text:
        return False
    if _looks_like_id(text):
        return False
    return True


def _extract_issue_id(contexts: list[Mapping[str, Any]]) -> str | None:
    preferred_keys = ("identifier", "key", "issueId", "issue_id")
    fallback_keys = ("id",)

    for key in preferred_keys:
        value = _first_string_for_key(contexts, key)
        if value:
            return value

    for key in fallback_keys:
        value = _first_string_for_key(contexts, key)
        if value:
            return value

    return None


def _extract_title(contexts: list[Mapping[str, Any]]) -> str | None:
    return _first_string_for_key(contexts, "title")


def _first_string_for_key(contexts: list[Mapping[str, Any]], key: str) -> str | None:
    for context in reversed(contexts):
        value = _string_value(context.get(key))
        if value:
            return value
    return None


def _has_prefix(title: str) -> bool:
    return title.strip().lower().startswith(PREFIX.lower())


def _normalize_text(value: Any) -> str | None:
    text = _string_value(value)
    if text is None:
        return None

    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = text.replace("_", " ").replace("-", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower() or None


def _string_value(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _looks_like_id(text: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-fA-F-]{16,}", text.strip()))


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 1

    update = build_issue_title_update(payload)
    if update:
        print(json.dumps(update, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
