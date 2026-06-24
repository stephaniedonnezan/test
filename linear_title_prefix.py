"""Build Linear issue title updates for Cursor research automation."""

from __future__ import annotations

import json
import re
import sys
from collections import deque
from collections.abc import Mapping, Sequence
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_DIRECT_STATUS_CHANGE_TRIGGERS = {
    "status changed",
    "status change",
    "status updated",
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
_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflowstate",
    "workflowstatus",
}
_TRIGGER_KEYS = {
    "trigger",
    "action",
    "type",
    "webhookType",
    "webhook_type",
    "eventType",
    "event_type",
}
_EXPLICIT_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "statusName",
    "status_name",
    "newState",
    "new_state",
    "newWorkflowState",
    "new_workflow_state",
    "workflowStateName",
    "workflow_state_name",
)
_CURRENT_STATUS_KEYS = ("status", "state", "workflowState", "workflow_state")
_ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "key", "id")
_TITLE_KEYS = ("title", "name")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to To Research.

    The automation payload can arrive as a flat Cursor trigger context or as a
    nested Linear webhook. The returned action is intentionally side-effect free
    so the caller can decide how to apply it.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    new_status = _find_new_status(event)
    if not _is_target_status(new_status):
        return None

    issue_id = _find_issue_id(event)
    title = _find_title(event)
    if not issue_id or not title:
        return None

    new_title = _prefixed_title(title)
    if new_title is None:
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": new_title,
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    triggers = {_normalize_text(value) for value in _collect_values(event, _TRIGGER_KEYS)}
    triggers.discard("")

    if triggers & _DIRECT_STATUS_CHANGE_TRIGGERS:
        return True

    if triggers & _UPDATE_TRIGGERS:
        return _status_field_was_updated(event)

    return _status_field_was_updated(event)


def _status_field_was_updated(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized_key = _normalize_field_name(key)
            if normalized_key in {
                "updatedfields",
                "updatedfield",
                "changedfields",
                "changedfield",
            }:
                if _sequence_mentions_status_field(child):
                    return True

            if normalized_key in {"changes", "changed", "updatedfrom"}:
                if _changes_mention_status_field(child):
                    return True

            if _status_field_was_updated(child):
                return True

    if _is_sequence(value):
        return any(_status_field_was_updated(item) for item in value)

    return False


def _sequence_mentions_status_field(value: Any) -> bool:
    if isinstance(value, Mapping):
        return _changes_mention_status_field(value)

    if not _is_sequence(value):
        return False

    for item in value:
        if isinstance(item, str) and _is_status_field_name(item):
            return True
        if isinstance(item, Mapping):
            field_name = _first_string_value(item, ("field", "name", "key"))
            if field_name and _is_status_field_name(field_name):
                return True

    return False


def _changes_mention_status_field(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if _is_status_field_name(key):
                return True
            if isinstance(child, Mapping):
                field_name = _first_string_value(child, ("field", "name", "key"))
                if field_name and _is_status_field_name(field_name):
                    return True
            if _changes_mention_status_field(child):
                return True

    if _is_sequence(value):
        return any(_changes_mention_status_field(item) for item in value)

    return False


def _find_new_status(event: Mapping[str, Any]) -> str | None:
    for value in _collect_values(event, _EXPLICIT_STATUS_KEYS):
        status = _coerce_status(value)
        if status:
            return status

    changed_status = _find_status_from_changes(event)
    if changed_status:
        return changed_status

    for value in _collect_values(event, _CURRENT_STATUS_KEYS):
        status = _coerce_status(value)
        if status:
            return status

    return None


def _find_status_from_changes(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if _is_status_field_name(key):
                status = _coerce_status_change_value(child)
                if status:
                    return status

            if _normalize_field_name(key) in {"changes", "changed", "updatedfrom"}:
                status = _coerce_status_change_value(child)
                if status:
                    return status

            status = _find_status_from_changes(child)
            if status:
                return status

    if _is_sequence(value):
        for item in value:
            status = _find_status_from_changes(item)
            if status:
                return status

    return None


def _coerce_status_change_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        field_name = _first_string_value(value, ("field", "key"))
        if field_name and not _is_status_field_name(field_name):
            return None

        for key in (
            "to",
            "toValue",
            "to_value",
            "new",
            "newValue",
            "new_value",
            "after",
            "current",
            "name",
        ):
            status = _coerce_status(value.get(key))
            if status:
                return status

    if _is_sequence(value):
        for item in value:
            status = _coerce_status_change_value(item)
            if status:
                return status

    return _coerce_status(value)


def _find_issue_id(event: Mapping[str, Any]) -> str | None:
    for context in _issue_contexts(event):
        issue_id = _first_string_value(context, _ISSUE_ID_KEYS)
        if issue_id:
            return issue_id
    return None


def _find_title(event: Mapping[str, Any]) -> str | None:
    for context in _issue_contexts(event):
        title = _first_string_value(context, _TITLE_KEYS)
        if title:
            return title
    return None


def _issue_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)

    trigger_context = event.get("triggerContext") or event.get("trigger_context")
    add(trigger_context)

    data = event.get("data")
    if isinstance(data, Mapping):
        add(data.get("issue"))
        add(data.get("node"))
        add(data)

    add(event.get("issue"))
    add(event.get("node"))
    add(event)
    return contexts


def _prefixed_title(title: str) -> str | None:
    clean_title = title.strip()
    if not clean_title:
        return None
    if re.match(rf"^{re.escape(PREFIX)}\b", clean_title, flags=re.IGNORECASE):
        return None
    return f"{PREFIX}: {clean_title}"


def _collect_values(value: Any, keys: set[str] | tuple[str, ...]) -> list[Any]:
    values: list[Any] = []
    queue: deque[Any] = deque([value])

    while queue:
        current = queue.popleft()
        if isinstance(current, Mapping):
            for key, child in current.items():
                if key in keys:
                    values.append(child)
                if isinstance(child, (Mapping, list, tuple)):
                    queue.append(child)
        elif _is_sequence(current):
            queue.extend(current)

    return values


def _coerce_status(value: Any) -> str | None:
    if isinstance(value, str):
        status = value.strip()
        return status or None

    if isinstance(value, Mapping):
        return _first_string_value(value, ("name", "title", "status"))

    return None


def _first_string_value(mapping: Mapping[str, Any], keys: Sequence[str]) -> str | None:
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, str):
            clean_value = value.strip()
            if clean_value:
                return clean_value
        if isinstance(value, Mapping):
            nested = _first_string_value(value, ("name", "title", "id"))
            if nested:
                return nested
    return None


def _is_target_status(value: str | None) -> bool:
    return _normalize_text(value) == TARGET_STATUS


def _is_status_field_name(value: Any) -> bool:
    return _normalize_field_name(value) in _STATUS_FIELD_NAMES


def _normalize_field_name(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value.strip())
    spaced = re.sub(r"[^A-Za-z0-9]+", " ", spaced)
    return re.sub(r"\s+", " ", spaced).strip().lower()


def _is_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON payload: {exc}", file=sys.stderr)
        return 2

    result = build_issue_title_update(payload)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
