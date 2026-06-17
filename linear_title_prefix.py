"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_DIRECT_STATUS_CHANGE_TOKENS = {
    "statuschanged",
    "statuschange",
    "statechanged",
    "statechange",
    "workflowstatechanged",
    "workflowstatechange",
}
_GENERIC_UPDATE_TOKENS = {
    "update",
    "updated",
    "issueupdate",
    "issueupdated",
    "updatedissue",
}
_STATUS_FIELD_TOKENS = {
    "status",
    "statusid",
    "state",
    "stateid",
    "workflowstate",
    "workflowstateid",
    "workflowstatus",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update action when an issue moves to "to research"."""

    if not isinstance(event, Mapping):
        return None

    context = _merged_context(event)
    if not _is_status_change_event(context):
        return None

    if not any(_is_target_status(status) for status in _new_status_values(context)):
        return None

    issue_id = _first_text(context, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_text(context, ("title",))
    if not issue_id or not title:
        return None

    clean_title = title.strip()
    if _has_prefix(clean_title):
        new_title = clean_title
    else:
        new_title = f"{PREFIX}: {clean_title}"

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": new_title,
    }


def _merged_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common Cursor and Linear webhook locations into one lookup map."""

    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping):
            contexts.append(value)

    trigger_context = event.get("triggerContext")
    data = event.get("data")
    issue = event.get("issue")

    if isinstance(data, Mapping):
        add(data.get("issue"))
    if isinstance(trigger_context, Mapping):
        trigger_data = trigger_context.get("data")
        if isinstance(trigger_data, Mapping):
            add(trigger_data.get("issue"))
            add(trigger_data)
        add(trigger_context.get("issue"))
    add(issue)
    add(data)
    add(trigger_context)
    add(event)

    merged: dict[str, Any] = {}
    for context in contexts:
        merged.update(context)
    return merged


def _is_status_change_event(context: Mapping[str, Any]) -> bool:
    event_keys = ("trigger", "event", "eventType", "webhookType", "action", "type")
    event_tokens = {_compact_token(context.get(key)) for key in event_keys if key in context}

    if any(_is_direct_status_change_token(token) for token in event_tokens):
        return True

    if event_tokens.intersection(_GENERIC_UPDATE_TOKENS):
        return _changed_fields_include_status(context)

    return _changed_fields_include_status(context)


def _is_direct_status_change_token(token: str) -> bool:
    return token in _DIRECT_STATUS_CHANGE_TOKENS or any(
        direct_token in token for direct_token in _DIRECT_STATUS_CHANGE_TOKENS
    )


def _changed_fields_include_status(context: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "changedFields", "changes", "updatedProperties", "changedProperties"):
        value = context.get(key)
        if _value_mentions_status_field(value):
            return True
    return False


def _value_mentions_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)

    if isinstance(value, Mapping):
        for key, nested_value in value.items():
            if _is_status_field(key):
                return True
            if isinstance(nested_value, Mapping):
                field_name = _first_text(nested_value, ("field", "name", "key", "property", "path"))
                if field_name and _is_status_field(field_name):
                    return True
        return False

    if isinstance(value, list | tuple | set):
        for item in value:
            if isinstance(item, Mapping):
                field_name = _first_text(item, ("field", "name", "key", "property", "path"))
                if field_name and _is_status_field(field_name):
                    return True
                if any(_is_status_field(key) for key in item):
                    return True
            elif _is_status_field(item):
                return True

    return False


def _new_status_values(context: Mapping[str, Any]) -> list[str]:
    values: list[str] = []

    for key in (
        "newStatus",
        "new_status",
        "toStatus",
        "newState",
        "new_state",
        "toState",
        "newWorkflowState",
        "new_workflow_state",
        "statusName",
        "stateName",
        "workflowStateName",
    ):
        values.extend(_text_values(context.get(key)))

    values.extend(_changed_status_values(context))

    for key in ("status", "state", "workflowState"):
        values.extend(_text_values(context.get(key)))

    return [value for value in values if value]


def _changed_status_values(context: Mapping[str, Any]) -> list[str]:
    values: list[str] = []
    for key in ("changes", "changedFields", "updatedFields"):
        changed = context.get(key)
        if isinstance(changed, Mapping):
            for field_name, change in changed.items():
                if _is_status_field(field_name):
                    values.extend(_new_value_texts(change))
        elif isinstance(changed, list | tuple | set):
            for item in changed:
                if isinstance(item, Mapping):
                    field_name = _first_text(item, ("field", "name", "key", "property", "path"))
                    if field_name and _is_status_field(field_name):
                        values.extend(_new_value_texts(item))
    return values


def _new_value_texts(value: Any) -> list[str]:
    if not isinstance(value, Mapping):
        return _text_values(value)

    values: list[str] = []
    for key in (
        "to",
        "toValue",
        "new",
        "newValue",
        "after",
        "current",
        "value",
        "name",
        "status",
        "state",
        "workflowState",
    ):
        values.extend(_text_values(value.get(key)))
    return values


def _text_values(value: Any) -> list[str]:
    if isinstance(value, str):
        stripped = value.strip()
        return [stripped] if stripped else []

    if isinstance(value, Mapping):
        for key in ("name", "title", "label", "displayName"):
            text = value.get(key)
            if isinstance(text, str) and text.strip():
                return [text.strip()]

    return []


def _first_text(context: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = context.get(key)
        if isinstance(value, str) and value.strip():
            return value
        if isinstance(value, int):
            return str(value)
    return None


def _is_target_status(value: str) -> bool:
    return _normalize_token(value) == TARGET_STATUS


def _is_status_field(value: Any) -> bool:
    return _compact_token(value) in _STATUS_FIELD_TOKENS


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def _compact_token(value: Any) -> str:
    return _normalize_token(value).replace(" ", "")


def _normalize_token(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    camel_spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    words = re.sub(r"[^A-Za-z0-9]+", " ", camel_spaced).strip().lower()
    return re.sub(r"\s+", " ", words)


def main() -> int:
    payload = json.load(sys.stdin)
    update = build_issue_title_update(payload)
    if update is None:
        return 0
    json.dump(update, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
