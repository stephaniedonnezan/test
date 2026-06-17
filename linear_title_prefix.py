"""Build Linear issue title updates for research-status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_DIRECT_STATUS_CHANGE_EVENTS = {
    "status changed",
    "status change",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
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
    "workflow status",
    "workflowstate",
    "state id",
    "status id",
    "workflow state id",
}
_EVENT_KEYS = {
    "trigger",
    "action",
    "type",
    "event",
    "eventType",
    "webhookAction",
}
_EXPLICIT_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "newWorkflowState",
    "new_workflow_state",
    "newWorkflowStatus",
    "targetStatus",
    "target_status",
    "toStatus",
    "to_status",
    "statusAfter",
    "status_after",
)
_FALLBACK_STATUS_KEYS = (
    "status",
    "state",
    "workflowState",
    "workflow_state",
    "workflowStatus",
    "workflow_status",
)
_ISSUE_ID_KEYS = ("issueId", "issue_id", "id", "identifier", "key")


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moved to research.

    The function is intentionally side-effect free. Automation runners can pass
    the returned action to their Linear update layer.
    """

    if not isinstance(event, Mapping):
        return None

    payloads = _payload_candidates(event)
    if not _is_status_change_event(payloads):
        return None

    new_status = _extract_new_status(payloads)
    if _normalize(new_status) != TARGET_STATUS:
        return None

    issue_id = _extract_first_text(payloads, _ISSUE_ID_KEYS)
    title = _extract_first_text(payloads, ("title", "name"))
    if not issue_id or not title:
        return None

    clean_title = title.strip()
    if not clean_title or clean_title.lower().startswith(TITLE_PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {clean_title}",
    }


def _payload_candidates(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return nested payload dictionaries from most-specific to least-specific."""

    candidates: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in candidates:
            candidates.append(value)

    trigger_context = event.get("triggerContext")
    data = event.get("data")
    issue = event.get("issue")

    if isinstance(trigger_context, Mapping):
        add(trigger_context)
        add(trigger_context.get("issue"))
        add(trigger_context.get("data"))
    if isinstance(data, Mapping):
        add(data.get("issue"))
        add(data)
    add(issue)
    add(event)

    # Keep useful nested issue/state dictionaries available without letting
    # them override outer event metadata in the earlier candidates.
    for payload in list(candidates):
        add(payload.get("state"))
        add(payload.get("workflowState"))
        add(payload.get("workflow_state"))

    return candidates


def _is_status_change_event(payloads: Iterable[Mapping[str, Any]]) -> bool:
    event_names = {
        normalized
        for payload in payloads
        for normalized in (_normalize(payload.get(key)) for key in _EVENT_KEYS)
        if normalized
    }
    if event_names & _DIRECT_STATUS_CHANGE_EVENTS:
        return True
    if event_names & _GENERIC_UPDATE_EVENTS:
        return _updated_fields_include_status(payloads)
    return False


def _updated_fields_include_status(payloads: Iterable[Mapping[str, Any]]) -> bool:
    for payload in payloads:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            if _field_collection_mentions_status(payload.get(key)):
                return True
        for key in ("changes", "updatedFrom", "updated_from"):
            if _change_mapping_mentions_status(payload.get(key)):
                return True
    return False


def _field_collection_mentions_status(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)
    if isinstance(value, Mapping):
        return any(_is_status_field(key) for key in value)
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        for item in value:
            if isinstance(item, Mapping):
                if any(_is_status_field(item.get(key)) for key in ("name", "field", "key")):
                    return True
            elif _is_status_field(item):
                return True
    return False


def _change_mapping_mentions_status(value: Any) -> bool:
    if not isinstance(value, Mapping):
        return False
    return any(_is_status_field(key) for key in value)


def _is_status_field(value: Any) -> bool:
    normalized = _normalize(value)
    return normalized in _STATUS_FIELD_NAMES or normalized.startswith("state ")


def _extract_new_status(payloads: Iterable[Mapping[str, Any]]) -> str | None:
    for payload in payloads:
        status = _extract_first_text([payload], _EXPLICIT_STATUS_KEYS)
        if status:
            return status

    for payload in payloads:
        for key in ("changes", "updatedFields", "updated_fields"):
            status = _extract_status_from_changes(payload.get(key))
            if status:
                return status

    return _extract_first_text(payloads, _FALLBACK_STATUS_KEYS)


def _extract_status_from_changes(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key, change in value.items():
            if _is_status_field(key):
                status = _extract_change_new_value(change)
                if status:
                    return status
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        for item in value:
            if isinstance(item, Mapping) and any(
                _is_status_field(item.get(key)) for key in ("name", "field", "key")
            ):
                status = _extract_change_new_value(item)
                if status:
                    return status
    return None


def _extract_change_new_value(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, Mapping):
        for key in ("newValue", "new_value", "to", "after", "new", "name"):
            text = _text_from_value(value.get(key))
            if text:
                return text
    return None


def _extract_first_text(
    payloads: Iterable[Mapping[str, Any]], keys: Iterable[str]
) -> str | None:
    for payload in payloads:
        for key in keys:
            if key not in payload:
                continue
            text = _text_from_value(payload.get(key))
            if text:
                return text
    return None


def _text_from_value(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            text = _text_from_value(value.get(key))
            if text:
                return text
    return None


def _normalize(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    spaced = re.sub(r"[^A-Za-z0-9]+", " ", spaced)
    return " ".join(spaced.lower().split())


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        json.dump(action, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
