"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_DIRECT_STATUS_CHANGE_EVENTS = {
    "status change",
    "status changed",
    "issue status change",
    "issue status changed",
    "state change",
    "state changed",
    "workflow state change",
    "workflow state changed",
}

_GENERIC_UPDATE_EVENTS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}

_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflow state",
    "workflowstate",
}

_ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "key", "id")
_TITLE_KEYS = ("title",)
_NEW_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "newWorkflowState",
    "new_workflow_state",
)
_CURRENT_STATUS_KEYS = ("status", "state", "workflowState", "workflow_state")
_TRIGGER_KEYS = (
    "trigger",
    "event",
    "eventType",
    "event_type",
    "action",
    "type",
    "webhookType",
    "webhook_type",
)
_UPDATED_FIELD_KEYS = (
    "updatedFields",
    "updated_fields",
    "changedFields",
    "changed_fields",
)
_CHANGE_KEYS = ("changes", "changed", "updated")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue title update action when a Linear issue enters research.

    The function is intentionally side-effect free so the surrounding automation
    can decide how to submit the returned update to Linear.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _ordered_contexts(event)
    if not _is_status_change_event(event):
        return None

    new_status = _extract_new_status(contexts)
    if _normalize_name(new_status) != TARGET_STATUS:
        return None

    issue_id = _first_string(contexts, _ISSUE_ID_KEYS)
    title = _first_string(contexts, _TITLE_KEYS)
    if not issue_id or not title:
        return None

    stripped_title = title.strip()
    if _has_research_prefix(stripped_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {stripped_title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    trigger_names = {
        normalized
        for context in _iter_mappings(event)
        for normalized in (_normalized_key_value(context, key) for key in _TRIGGER_KEYS)
        if normalized
    }

    if trigger_names & _DIRECT_STATUS_CHANGE_EVENTS:
        return True

    if trigger_names & _GENERIC_UPDATE_EVENTS:
        return _has_status_field_change(event)

    return _has_status_field_change(event)


def _has_status_field_change(event: Mapping[str, Any]) -> bool:
    for context in _iter_mappings(event):
        for key in _UPDATED_FIELD_KEYS:
            if _contains_status_field(context.get(key)):
                return True

        for key in _CHANGE_KEYS:
            changes = context.get(key)
            if isinstance(changes, Mapping):
                if any(_is_status_field_name(field) for field in changes):
                    return True
            elif _contains_status_field(changes):
                return True

    return False


def _extract_new_status(contexts: Iterable[Mapping[str, Any]]) -> Any:
    context_list = list(contexts)

    for context in context_list:
        for key in _NEW_STATUS_KEYS:
            if key in context:
                return context[key]

    for context in context_list:
        changed_status = _status_from_changes(context)
        if changed_status is not None:
            return changed_status

    for context in context_list:
        for key in _CURRENT_STATUS_KEYS:
            if key in context:
                return context[key]

    return None


def _status_from_changes(context: Mapping[str, Any]) -> Any:
    for key in _CHANGE_KEYS:
        changes = context.get(key)
        if not isinstance(changes, Mapping):
            continue

        for field, value in changes.items():
            if not _is_status_field_name(field):
                continue

            if isinstance(value, Mapping):
                for status_key in ("to", "new", "after", "current", "value"):
                    if status_key in value:
                        return value[status_key]
            return value

    return None


def _ordered_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    paths = (
        ("triggerContext",),
        ("automation_trigger_info", "triggerContext"),
        ("triggerContext", "issue"),
        ("automation_trigger_info", "triggerContext", "issue"),
        ("data", "issue"),
        ("payload", "data", "issue"),
        ("issue",),
        ("payload", "issue"),
        ("data",),
        ("payload", "data"),
        ("payload",),
        (),
    )

    contexts: list[Mapping[str, Any]] = []
    seen: set[int] = set()
    for path in paths:
        value: Any = event
        for part in path:
            if not isinstance(value, Mapping):
                value = None
                break
            value = value.get(part)

        if isinstance(value, Mapping) and id(value) not in seen:
            contexts.append(value)
            seen.add(id(value))

    return contexts


def _iter_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for nested in value.values():
            yield from _iter_mappings(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _iter_mappings(nested)


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field_name(value)

    if isinstance(value, Mapping):
        field_name = (
            value.get("field")
            or value.get("fieldName")
            or value.get("field_name")
            or value.get("name")
            or value.get("key")
        )
        return _is_status_field_name(field_name)

    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        return any(_contains_status_field(item) for item in value)

    return False


def _first_string(contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _normalized_key_value(context: Mapping[str, Any], key: str) -> str | None:
    if key not in context:
        return None
    return _normalize_name(context[key])


def _normalize_name(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("name", "title", "label", "value"):
            normalized = _normalize_name(value.get(key))
            if normalized:
                return normalized
        return None

    if not isinstance(value, str):
        return None

    separated = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value.strip())
    normalized = re.sub(r"[^a-zA-Z0-9]+", " ", separated).strip().lower()
    return re.sub(r"\s+", " ", normalized) or None


def _is_status_field_name(value: Any) -> bool:
    normalized = _normalize_name(value)
    return bool(normalized and normalized in _STATUS_FIELD_NAMES)


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    update = build_issue_title_update(payload)
    if update is None:
        return 0

    print(json.dumps(update, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
