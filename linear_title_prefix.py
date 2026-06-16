"""Build Linear issue title updates for Cursor research status changes.

The automation receives Linear webhook-shaped payloads from a few sources.  This
module keeps the side effect out of the handler: callers can send the returned
action to the integration that updates the issue title.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


RESEARCH_STATUS = "to research"
TITLE_PREFIX = "Cursor researching"

_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "state id",
    "workflow state",
    "workflow state id",
    "workflowstate",
    "workflowstateid",
}

_DIRECT_STATUS_TRIGGERS = {
    "status changed",
    "status change",
    "status updated",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
}

_GENERIC_UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title-update action when an issue moves to research.

    The returned shape is intentionally small and serializable:

    ``{"action": "update_issue_title", "issueId": "...", "title": "..."}``
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _ordered_contexts(event)
    if not _is_status_change_event(contexts):
        return None

    new_status = _extract_new_status(contexts)
    if _normalize_token(new_status) != RESEARCH_STATUS:
        return None

    issue_id = _first_text(contexts, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_text(contexts, ("title",))
    if issue_id is None or title is None:
        return None

    title = title.strip()
    if not title or title.lower().startswith(TITLE_PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _ordered_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return payload fragments in a useful extraction order."""

    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)

    trigger_context = event.get("triggerContext")
    data = event.get("data")
    issue = event.get("issue")

    add(trigger_context)
    if isinstance(data, Mapping):
        add(data.get("issue"))
    add(issue)
    add(data)
    add(event)

    return contexts


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    trigger_values = [
        _normalize_token(value)
        for context in contexts
        for key in ("trigger", "action", "type", "event", "eventType", "webhookType")
        if (value := _nested_get(context, key)) is not None
    ]

    if any(value in _DIRECT_STATUS_TRIGGERS for value in trigger_values):
        return True

    return any(value in _GENERIC_UPDATE_TRIGGERS for value in trigger_values) and _has_status_change_marker(
        contexts
    )


def _has_status_change_marker(contexts: Iterable[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "changedFields"):
            if _has_status_field(context.get(key)):
                return True

        changes = context.get("changes")
        if isinstance(changes, Mapping) and _has_status_field(changes.keys()):
            return True

        updated_from = context.get("updatedFrom")
        if isinstance(updated_from, Mapping) and _has_status_field(updated_from.keys()):
            return True

    return False


def _has_status_field(fields: Any) -> bool:
    if isinstance(fields, str):
        candidates = (fields,)
    elif isinstance(fields, Mapping):
        candidates = fields.keys()
    elif isinstance(fields, Iterable):
        candidates = fields
    else:
        return False

    for field in candidates:
        if isinstance(field, Mapping):
            field = field.get("name") or field.get("field") or field.get("key")
        normalized = _normalize_token(field)
        if normalized in _STATUS_FIELD_NAMES:
            return True
    return False


def _extract_new_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    explicit_keys = (
        "newStatus",
        "new_status",
        "toStatus",
        "to_status",
        "newState",
        "new_state",
        "toState",
        "to_state",
        "newWorkflowState",
        "new_workflow_state",
    )
    current_keys = (
        "status",
        "state",
        "workflowState",
        "workflow_state",
        "statusName",
        "status_name",
        "stateName",
        "state_name",
    )

    contexts = list(contexts)

    for context in contexts:
        status = _first_text((context,), explicit_keys)
        if status:
            return status

    for context in contexts:
        changes = context.get("changes")
        if not isinstance(changes, Mapping):
            continue
        for key, value in changes.items():
            if _normalize_token(key) in _STATUS_FIELD_NAMES:
                status = _status_from_change(value)
                if status:
                    return status

    for context in contexts:
        status = _first_text((context,), current_keys)
        if status:
            return status

    return None


def _status_from_change(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("to", "new", "newValue", "new_value", "after", "current"):
            status = _string_value(value.get(key))
            if status:
                return status
    elif isinstance(value, list) and value:
        return _string_value(value[-1])
    return _string_value(value)


def _first_text(contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for context in contexts:
        for key in keys:
            value = _nested_get(context, key)
            text = _string_value(value)
            if text:
                return text
    return None


def _nested_get(context: Mapping[str, Any], key: str) -> Any:
    if key in context:
        return context[key]

    normalized_key = _normalize_token(key)
    for candidate_key, value in context.items():
        if _normalize_token(candidate_key) == normalized_key:
            return value
    return None


def _string_value(value: Any) -> str | None:
    if isinstance(value, str):
        text = value.strip()
        return text or None
    if isinstance(value, Mapping):
        for key in ("name", "title", "label", "value"):
            text = _string_value(value.get(key))
            if text:
                return text
    return None


def _normalize_token(value: Any) -> str:
    if value is None:
        return ""

    text = _string_value(value)
    if text is None:
        text = str(value)

    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"invalid JSON: {exc}", file=sys.stderr)
        return 2

    action = build_issue_title_update(event)
    if action is None:
        return 0

    print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
