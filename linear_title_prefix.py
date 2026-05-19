"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_CONTAINER_KEYS = (
    "triggerContext",
    "trigger_context",
    "data",
    "issue",
    "payload",
    "webhook",
    "resource",
)
_ID_KEYS = ("id", "issueId", "issue_id", "identifier")
_TITLE_KEYS = ("title",)
_EXPLICIT_STATUS_KEYS = ("newStatus", "new_status", "newState", "new_state")
_STATUS_KEYS = (
    "status",
    "state",
    "workflowState",
    "workflow_state",
)
_TRIGGER_KEYS = (
    "trigger",
    "action",
    "type",
    "webhookType",
    "webhook_type",
    "event",
    "eventType",
    "event_type",
)
_UPDATED_FIELD_KEYS = (
    "updatedFields",
    "updated_fields",
    "changedFields",
    "changed_fields",
)
_UPDATED_FROM_KEYS = (
    "updatedFrom",
    "updated_from",
    "previousValues",
    "previous_values",
    "changes",
)
_STATUS_FIELD_NAMES = {
    "status",
    "statusid",
    "state",
    "stateid",
    "workflowstate",
    "workflowstateid",
}
_DIRECT_STATUS_CHANGE_TRIGGERS = {
    "status changed",
    "status change",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
}
_UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Any) -> dict[str, str] | None:
    """Return a title-update action when a Linear issue moves to To Research."""

    if not isinstance(event, Mapping):
        return None

    contexts = _payload_contexts(event)
    if not _is_status_change(contexts):
        return None

    status = _extract_new_status(contexts)
    if _normalize_label(status) != _normalize_label(TARGET_STATUS):
        return None

    issue_id = _first_text(contexts, _ID_KEYS)
    title = _first_text(contexts, _TITLE_KEYS)
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_title_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _payload_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []
    seen: set[int] = set()

    def add_context(value: Any) -> None:
        if not isinstance(value, Mapping):
            return

        value_id = id(value)
        if value_id in seen:
            return
        seen.add(value_id)

        contexts.append(value)
        for key in _CONTAINER_KEYS:
            add_context(value.get(key))

    add_context(event)
    return contexts


def _is_status_change(contexts: Sequence[Mapping[str, Any]]) -> bool:
    saw_update_trigger = False

    for context in contexts:
        for key in _TRIGGER_KEYS:
            trigger = _normalize_label(context.get(key))
            if trigger in _DIRECT_STATUS_CHANGE_TRIGGERS:
                return True
            if trigger in _UPDATE_TRIGGERS:
                saw_update_trigger = True

    return saw_update_trigger and _updated_payload_mentions_status(contexts)


def _updated_payload_mentions_status(contexts: Sequence[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in _UPDATED_FIELD_KEYS:
            if _contains_status_field(context.get(key)):
                return True

        for key in _UPDATED_FROM_KEYS:
            value = context.get(key)
            if isinstance(value, Mapping):
                if any(_is_status_field(field) for field in value):
                    return True
            elif _contains_status_field(value):
                return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)

    if isinstance(value, Mapping):
        return any(_is_status_field(field) for field in value)

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return any(_contains_status_field(item) for item in value)

    return False


def _is_status_field(value: Any) -> bool:
    return _normalize_field(value) in _STATUS_FIELD_NAMES


def _extract_new_status(contexts: Sequence[Mapping[str, Any]]) -> str:
    for keys in (_EXPLICIT_STATUS_KEYS, _STATUS_KEYS):
        text = _first_text(contexts, keys)
        if text:
            return text

    return ""


def _first_text(contexts: Sequence[Mapping[str, Any]], keys: Sequence[str]) -> str:
    for context in contexts:
        for key in keys:
            text = _text_value(context.get(key))
            if text:
                return text

    return ""


def _text_value(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, str):
        return value.strip()

    if isinstance(value, (int, float)):
        return str(value).strip()

    if isinstance(value, Mapping):
        for key in ("name", "title", "label", "value", "id", "identifier"):
            text = _text_value(value.get(key))
            if text:
                return text

    return ""


def _has_title_prefix(title: str) -> bool:
    return _normalize_label(title).startswith(_normalize_label(TITLE_PREFIX))


def _normalize_label(value: Any) -> str:
    text = _text_value(value)
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.casefold().split())


def _normalize_field(value: Any) -> str:
    text = _text_value(value)
    return re.sub(r"[^A-Za-z0-9]+", "", text).casefold()


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        json.dump(update, sys.stdout)
        sys.stdout.write("\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
