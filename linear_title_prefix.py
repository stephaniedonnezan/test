"""Build Linear issue title updates for research status changes.

The automation should update an issue title only when a Linear issue status
change moves the issue into "to research".
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflowstatus"}
ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "key", "id")
TITLE_KEYS = ("title", "name")
EXPLICIT_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "toStatus",
    "to_status",
    "newState",
    "new_state",
)
CURRENT_STATUS_KEYS = (
    "status",
    "state",
    "workflowState",
    "workflowStatus",
)


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title-update action for matching Linear status-change events."""

    if not isinstance(event, Mapping):
        return None

    contexts = _payload_contexts(event)
    if not _is_status_change_event(contexts):
        return None

    new_status = _extract_new_status(contexts)
    if _normalize_words(new_status) != TARGET_STATUS:
        return None

    issue_id = _first_text(contexts, ISSUE_ID_KEYS)
    title = _first_text(contexts, TITLE_KEYS)
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_title_prefix(title):
        updated_title = title
    else:
        updated_title = f"{TITLE_PREFIX}: {title}"

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": updated_title,
    }


def _payload_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return likely metadata and issue objects, outermost first."""

    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)

    add(event)
    trigger_context = event.get("triggerContext")
    add(trigger_context)

    data = event.get("data")
    add(data)
    if isinstance(data, Mapping):
        add(data.get("issue"))

    if isinstance(trigger_context, Mapping):
        add(trigger_context.get("data"))
        add(trigger_context.get("issue"))

    add(event.get("issue"))

    return contexts


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("trigger", "webhookType", "action", "type"):
            event_name = _normalize_words(context.get(key))
            if event_name in {
                "status changed",
                "status change",
                "state changed",
                "state change",
                "workflow state changed",
                "workflow state change",
                "workflow status changed",
                "workflow status change",
            }:
                return True

            if event_name in {"update", "updated", "issue update", "issue updated", "updated issue"}:
                if _status_field_changed(context):
                    return True

        if _status_field_changed(context):
            return True

    return False


def _status_field_changed(context: Mapping[str, Any]) -> bool:
    updated_fields = context.get("updatedFields") or context.get("updated_fields")
    if _contains_status_field(updated_fields):
        return True

    changes = context.get("changes") or context.get("changedFields") or context.get("changed_fields")
    if isinstance(changes, Mapping):
        return any(_is_status_field(key) for key in changes)
    if isinstance(changes, list):
        for change in changes:
            if isinstance(change, Mapping):
                field_name = change.get("field") or change.get("fieldName") or change.get("name")
                if _is_status_field(field_name):
                    return True
            elif _is_status_field(change):
                return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)
    if isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray, Mapping)):
        return any(_is_status_field(item) for item in value)
    return False


def _is_status_field(value: Any) -> bool:
    normalized = _normalize_compact(value)
    return normalized in STATUS_FIELD_NAMES


def _extract_new_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    contexts_list = list(contexts)

    for context in contexts_list:
        value = _first_status_text(context, EXPLICIT_STATUS_KEYS)
        if value:
            return value

    for context in contexts_list:
        value = _status_from_changes(context)
        if value:
            return value

    for context in contexts_list:
        value = _first_status_text(context, CURRENT_STATUS_KEYS)
        if value:
            return value

    return None


def _status_from_changes(context: Mapping[str, Any]) -> str | None:
    changes = context.get("changes") or context.get("changedFields") or context.get("changed_fields")
    if not isinstance(changes, Mapping):
        return None

    for field_name, change in changes.items():
        if not _is_status_field(field_name):
            continue

        if isinstance(change, Mapping):
            value = _first_status_text(
                change,
                ("newValue", "new_value", "to", "after", "value", "name", "displayName"),
            )
            if value:
                return value
        else:
            value = _text(change)
            if value:
                return value

    return None


def _first_status_text(context: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for key in keys:
        if key not in context:
            continue
        value = context.get(key)
        if isinstance(value, Mapping):
            nested = _first_text([value], ("name", "displayName", "title"))
            if nested:
                return nested
            continue
        text = _text(value)
        if text:
            return text
    return None


def _first_text(contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            text = _text(value)
            if text:
                return text
    return None


def _text(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value
    return None


def _has_title_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def _normalize_compact(value: Any) -> str:
    return _normalize_words(value).replace(" ", "")


def _normalize_words(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    words = re.sub(r"[^A-Za-z0-9]+", " ", spaced).strip().lower()
    return re.sub(r"\s+", " ", words)


def main() -> int:
    """Read a JSON event from stdin and print the requested update action."""

    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    action = build_issue_title_update(event)
    print(json.dumps(action))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
