"""Build title update actions for Linear issues entering research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_KEYS = {"status", "state", "workflowstate", "workflow_state"}
_DIRECT_STATUS_CHANGE_EVENTS = {
    "status changed",
    "state changed",
    "workflow state changed",
    "issue status changed",
    "issue state changed",
    "issue workflow state changed",
}
_GENERIC_UPDATE_EVENTS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear issue title update action for research status changes.

    The automation runner applies the returned action. Non-matching payloads are
    ignored by returning ``None``.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    status = _extract_new_status(event)
    if _normalize_text(status) != TARGET_STATUS:
        return None

    issue_id = _extract_issue_id(event)
    title = _extract_title(event)
    if not issue_id or not title or _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    trigger_values = [
        _normalize_text(value)
        for value in _iter_values_for_keys(
            event,
            {"trigger", "action", "type", "webhookType", "webhook_type", "event"},
        )
        if isinstance(value, str)
    ]

    if any(value in _DIRECT_STATUS_CHANGE_EVENTS for value in trigger_values):
        return True

    return any(value in _GENERIC_UPDATE_EVENTS for value in trigger_values) and _updated_fields_include_status(event)


def _updated_fields_include_status(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, nested_value in value.items():
            normalized_key = _normalize_key(key)
            if normalized_key in {"updatedfields", "updated_fields", "changedfields", "changed_fields"}:
                if _field_collection_includes_status(nested_value):
                    return True
            if normalized_key in {"changes", "changed"} and isinstance(nested_value, Mapping):
                if any(_normalize_key(change_key) in _STATUS_FIELD_KEYS for change_key in nested_value):
                    return True
            if _updated_fields_include_status(nested_value):
                return True
    elif isinstance(value, list):
        return any(_updated_fields_include_status(item) for item in value)

    return False


def _field_collection_includes_status(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_key(value) in _STATUS_FIELD_KEYS
    if isinstance(value, Mapping):
        return any(
            _normalize_key(key) in _STATUS_FIELD_KEYS or _field_collection_includes_status(nested_value)
            for key, nested_value in value.items()
        )
    if isinstance(value, Iterable):
        return any(_field_collection_includes_status(item) for item in value)
    return False


def _extract_new_status(event: Mapping[str, Any]) -> str | None:
    for context in _issue_contexts(event):
        for key in (
            "newStatus",
            "new_status",
            "newState",
            "new_state",
            "toStatus",
            "to_status",
            "toState",
            "to_state",
        ):
            status = _status_string(context.get(key))
            if status:
                return status

    changed_status = _status_from_changes(event)
    if changed_status:
        return changed_status

    for context in _issue_contexts(event):
        for key in ("status", "state", "workflowState", "workflow_state", "statusName", "stateName"):
            status = _status_string(context.get(key))
            if status:
                return status

    return None


def _status_from_changes(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key, nested_value in value.items():
            normalized_key = _normalize_key(key)
            if normalized_key in {"changes", "changed"} and isinstance(nested_value, Mapping):
                for change_key, change_value in nested_value.items():
                    if _normalize_key(change_key) in _STATUS_FIELD_KEYS:
                        status = _status_from_change_value(change_value)
                        if status:
                            return status
            status = _status_from_changes(nested_value)
            if status:
                return status
    elif isinstance(value, list):
        for item in value:
            status = _status_from_changes(item)
            if status:
                return status
    return None


def _status_from_change_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("new", "newValue", "new_value", "to", "after", "current", "value"):
            status = _status_string(value.get(key))
            if status:
                return status
    return _status_string(value)


def _status_string(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    if isinstance(value, Mapping):
        for key in ("name", "title", "label", "status", "state", "workflowState", "workflow_state"):
            status = _status_string(value.get(key))
            if status:
                return status
    return None


def _extract_issue_id(event: Mapping[str, Any]) -> str | None:
    for context in _issue_contexts(event):
        for key in ("issueId", "issue_id", "identifier", "key", "id"):
            if key == "id" and context is event and "automationId" in event:
                continue
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _extract_title(event: Mapping[str, Any]) -> str | None:
    for context in _issue_contexts(event):
        for key in ("title", "name", "summary"):
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _issue_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)

    trigger_context = event.get("triggerContext")
    data = event.get("data")
    issue = event.get("issue")
    payload = event.get("payload")

    add(trigger_context)
    if isinstance(data, Mapping):
        add(data.get("issue"))
    add(issue)
    if isinstance(payload, Mapping):
        add(payload.get("issue"))
    add(data)
    add(payload)
    add(event)

    return contexts


def _iter_values_for_keys(value: Any, keys: set[str]) -> Iterable[Any]:
    if isinstance(value, Mapping):
        for key, nested_value in value.items():
            if key in keys:
                yield nested_value
            yield from _iter_values_for_keys(nested_value, keys)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_values_for_keys(item, keys)


def _has_prefix(title: str) -> bool:
    return title.strip().lower().startswith(PREFIX.lower())


def _normalize_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9_]", "", _split_camel_case(str(value)).lower())


def _normalize_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = _split_camel_case(value)
    text = re.sub(r"[^a-z0-9]+", " ", text.lower())
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def _split_camel_case(value: str) -> str:
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    return re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", value)


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
