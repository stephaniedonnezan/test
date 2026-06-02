"""Build Linear issue title updates for research status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
UPDATE_ACTION = "update_issue_title"

_STATUS_CHANGE_VALUES = {
    "status changed",
    "status change",
    "status updated",
    "status update",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
}
_ISSUE_UPDATE_VALUES = {
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
_EXPLICIT_NEW_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "newWorkflowState",
    "new_workflow_state",
)
_STATUS_KEYS = ("status", "state", "workflowState", "workflow_state")
_ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "id")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue enters To Research.

    The automation payload can arrive either as the flat trigger context used by
    Cursor Automations or as a nested Linear webhook payload. This function only
    emits an action when the payload represents a status/state change whose new
    status is "to research".
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    new_status = _extract_new_status(event)
    if _normalize(new_status) != "to research":
        return None

    title = _extract_title(event)
    issue_id = _extract_issue_id(event)
    if not title or not issue_id:
        return None

    if _has_title_prefix(title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title.strip()}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    trigger_values = _values_for_keys(
        event,
        {"trigger", "action", "type", "eventType", "event_type", "webhookType"},
    )
    normalized_triggers = {_normalize(value) for value in trigger_values}

    if normalized_triggers & _STATUS_CHANGE_VALUES:
        return True

    if normalized_triggers & _ISSUE_UPDATE_VALUES:
        return _payload_updated_status(event)

    return False


def _payload_updated_status(event: Mapping[str, Any]) -> bool:
    updated_fields = _values_for_keys(
        event,
        {"updatedFields", "updated_fields", "changedFields", "changed_fields"},
    )
    return any(_is_status_field(value) for value in updated_fields)


def _is_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize(value) in _STATUS_FIELD_NAMES

    if isinstance(value, Mapping):
        return any(_is_status_field(key) for key in value.keys())

    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        return any(_is_status_field(item) for item in value)

    return False


def _extract_new_status(event: Mapping[str, Any]) -> str | None:
    candidates = _preferred_mappings(event)

    for mapping in candidates:
        for key in _EXPLICIT_NEW_STATUS_KEYS:
            status = _status_value(mapping.get(key))
            if status:
                return status

    for mapping in candidates:
        for key in _STATUS_KEYS:
            status = _status_value(mapping.get(key))
            if status:
                return status

    return None


def _status_value(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            nested = value.get(key)
            if isinstance(nested, str) and nested.strip():
                return nested.strip()

    return None


def _extract_title(event: Mapping[str, Any]) -> str | None:
    for mapping in _preferred_issue_mappings(event):
        title = mapping.get("title")
        if isinstance(title, str) and title.strip():
            return title.strip()

    return None


def _extract_issue_id(event: Mapping[str, Any]) -> str | None:
    for mapping in _preferred_issue_mappings(event):
        for key in _ISSUE_ID_KEYS:
            issue_id = mapping.get(key)
            if isinstance(issue_id, str) and issue_id.strip():
                return issue_id.strip()

    return None


def _preferred_mappings(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    mappings: list[Mapping[str, Any]] = [event]

    for key in ("triggerContext", "trigger_context", "data", "issue"):
        value = event.get(key)
        if isinstance(value, Mapping):
            mappings.append(value)

    data = event.get("data")
    if isinstance(data, Mapping):
        for key in ("issue", "state", "workflowState", "workflow_state"):
            value = data.get(key)
            if isinstance(value, Mapping):
                mappings.append(value)

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        for key in ("state", "workflowState", "workflow_state"):
            value = issue.get(key)
            if isinstance(value, Mapping):
                mappings.append(value)

    return _dedupe_mappings(mappings)


def _preferred_issue_mappings(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    mappings: list[Mapping[str, Any]] = []

    for key in ("issue", "triggerContext", "trigger_context", "data"):
        value = event.get(key)
        if isinstance(value, Mapping):
            mappings.append(value)

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            mappings.insert(0, issue)

    if event.get("title") or event.get("id") or event.get("issueId"):
        mappings.append(event)

    return _dedupe_mappings(mappings)


def _dedupe_mappings(mappings: list[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    seen: set[int] = set()
    deduped: list[Mapping[str, Any]] = []
    for mapping in mappings:
        mapping_id = id(mapping)
        if mapping_id not in seen:
            seen.add(mapping_id)
            deduped.append(mapping)
    return deduped


def _values_for_keys(value: Any, keys: set[str]) -> list[Any]:
    values: list[Any] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            if key in keys:
                values.append(child)
            values.extend(_values_for_keys(child, keys))
    elif isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        for child in value:
            values.extend(_values_for_keys(child, keys))
    return values


def _has_title_prefix(title: str) -> bool:
    return title.lstrip().lower().startswith(TITLE_PREFIX.lower())


def _normalize(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    with_word_boundaries = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    lower_value = with_word_boundaries.lower()
    words = re.sub(r"[^a-z0-9]+", " ", lower_value).strip().split()
    return " ".join(words)


def main() -> int:
    """Read an event JSON payload from stdin and print the update action."""

    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON payload: {exc}", file=sys.stderr)
        return 1

    action = build_issue_title_update(event)
    if action:
        print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
