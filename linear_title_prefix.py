"""Build Linear issue title updates for research-status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"

_EVENT_KEYS = ("trigger", "webhookType", "webhook_type", "action", "type")
_UPDATED_FIELD_KEYS = ("updatedFields", "updated_fields", "changedFields", "changed_fields")
_STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow_state"}
_NEW_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "statusName",
    "status_name",
    "stateName",
    "state_name",
    "workflowStateName",
    "workflow_state_name",
)
_STATUS_KEYS = ("status", "state", "workflowState", "workflow_state")
_TITLE_KEYS = ("title", "name")
_ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "key", "id")


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to research."""
    if not isinstance(event, Mapping):
        return None

    payloads = _payload_candidates(event)
    if not _is_status_change_event(payloads):
        return None

    new_status = _extract_new_status(payloads)
    if _normalize_words(new_status) != RESEARCH_STATUS:
        return None

    title = _extract_text(payloads, _TITLE_KEYS)
    issue_id = _extract_text(payloads, _ISSUE_ID_KEYS)
    if not title or not issue_id:
        return None

    if _has_research_prefix(title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _payload_candidates(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return useful payload layers, preferring outer metadata before issue data."""
    candidates: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in candidates:
            candidates.append(value)

    def walk(value: Any) -> None:
        if not isinstance(value, Mapping):
            return
        add(value)
        for key in ("automation_trigger_info", "triggerContext", "trigger_context", "data", "issue"):
            nested = value.get(key)
            if isinstance(nested, Mapping):
                walk(nested)

    walk(event)
    return candidates


def _is_status_change_event(payloads: list[Mapping[str, Any]]) -> bool:
    event_markers = [
        _normalize_words(payload[key])
        for payload in payloads
        for key in _EVENT_KEYS
        if key in payload
    ]

    if any(marker == "status changed" for marker in event_markers):
        return True

    update_markers = {"update", "updated", "issue update", "issue updated", "updated issue"}
    if any(marker in update_markers for marker in event_markers):
        return _updated_fields_include_status(payloads) or _changes_include_status(payloads)

    return _updated_fields_include_status(payloads) or _changes_include_status(payloads)


def _updated_fields_include_status(payloads: list[Mapping[str, Any]]) -> bool:
    for payload in payloads:
        for key in _UPDATED_FIELD_KEYS:
            value = payload.get(key)
            if isinstance(value, str):
                if _normalize_field_name(value) in _STATUS_FIELD_NAMES:
                    return True
            elif isinstance(value, list):
                if any(_normalize_field_name(item) in _STATUS_FIELD_NAMES for item in value):
                    return True
    return False


def _changes_include_status(payloads: list[Mapping[str, Any]]) -> bool:
    for payload in payloads:
        changes = payload.get("changes")
        if not isinstance(changes, Mapping):
            continue

        if any(_normalize_field_name(key) in _STATUS_FIELD_NAMES for key in changes):
            return True

        for key in ("field", "name", "updatedField"):
            if _normalize_field_name(changes.get(key)) in _STATUS_FIELD_NAMES:
                return True

    return False


def _extract_new_status(payloads: list[Mapping[str, Any]]) -> str | None:
    for payload in payloads:
        for key in _NEW_STATUS_KEYS:
            value = _extract_status_value(payload.get(key))
            if value:
                return value

    changed_status = _extract_status_from_changes(payloads)
    if changed_status:
        return changed_status

    for payload in payloads:
        for key in _STATUS_KEYS:
            value = _extract_status_value(payload.get(key))
            if value:
                return value

    return None


def _extract_status_from_changes(payloads: list[Mapping[str, Any]]) -> str | None:
    for payload in payloads:
        changes = payload.get("changes")
        if not isinstance(changes, Mapping):
            continue

        status_change = _first_status_change(changes)
        if status_change is not None:
            value = _extract_new_value(status_change)
            if value:
                return value

        if any(_normalize_field_name(changes.get(key)) in _STATUS_FIELD_NAMES for key in ("field", "name", "updatedField")):
            value = _extract_new_value(changes)
            if value:
                return value

    return None


def _first_status_change(changes: Mapping[str, Any]) -> Any:
    for key, value in changes.items():
        if _normalize_field_name(key) in _STATUS_FIELD_NAMES:
            return value
    return None


def _extract_new_value(change: Any) -> str | None:
    if isinstance(change, Mapping):
        for key in ("newValue", "new_value", "to", "after", "value", "name"):
            value = _extract_status_value(change.get(key))
            if value:
                return value
    return _extract_status_value(change)


def _extract_text(payloads: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for payload in reversed(payloads):
        for key in keys:
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _extract_status_value(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            nested = value.get(key)
            if isinstance(nested, str) and nested.strip():
                return nested.strip()
    return None


def _has_research_prefix(title: str) -> bool:
    return title.lstrip().lower().startswith(TITLE_PREFIX.lower())


def _normalize_words(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    with_word_boundaries = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value.strip())
    words = re.sub(r"[^A-Za-z0-9]+", " ", with_word_boundaries).lower().split()
    return " ".join(words)


def _normalize_field_name(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^A-Za-z0-9_]+", "", value).lower()


def main() -> int:
    """Read a JSON event from stdin and print the update action, if any."""
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
