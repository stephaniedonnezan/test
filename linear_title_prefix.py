"""Build Linear issue title updates for research-status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections import deque
from collections.abc import Mapping, Sequence
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_TRIGGER_KEYS = ("trigger", "webhookType", "action", "type", "event", "eventType")
_DIRECT_STATUS_CHANGE_TRIGGERS = {
    "status changed",
    "status change",
    "status updated",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
}
_ISSUE_UPDATE_TRIGGERS = {
    "issue updated",
    "updated issue",
    "issue update",
    "update",
    "updated",
}
_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflow state",
    "workflowstate",
    "workflow state name",
}
_NEW_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "newWorkflowState",
    "new_workflow_state",
    "statusName",
    "stateName",
    "workflowStateName",
)
_CURRENT_STATUS_KEYS = ("status", "state", "workflowState", "workflow_state")
_ISSUE_ID_KEYS = ("issueId", "issue_id", "id", "identifier", "key")
_TITLE_KEYS = ("title", "issueTitle", "issue_title")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear issue-title update action for "to research" transitions.

    The automation payloads can arrive as a flat trigger context, wrapped under
    ``triggerContext``, or as a nested Linear webhook payload. This function
    accepts those shapes and returns a small action object for the caller to
    apply, or ``None`` when the event should be ignored.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    if _normalize_label(_extract_new_status(event)) != TARGET_STATUS:
        return None

    issue_id = _extract_first_text(event, _ISSUE_ID_KEYS)
    title = _extract_first_text(event, _TITLE_KEYS)
    if issue_id is None or title is None:
        return None

    clean_title = title.strip()
    if _has_research_prefix(clean_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {clean_title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    trigger_values = [
        _normalize_label(value)
        for candidate in _mapping_candidates(event)
        for key, value in candidate.items()
        if key in _TRIGGER_KEYS
    ]

    if any(value in _DIRECT_STATUS_CHANGE_TRIGGERS for value in trigger_values):
        return True

    return any(value in _ISSUE_UPDATE_TRIGGERS for value in trigger_values) and _changed_fields_include_status(event)


def _changed_fields_include_status(event: Mapping[str, Any]) -> bool:
    for candidate in _mapping_candidates(event):
        for key in ("updatedFields", "changedFields", "changes", "updatedFrom", "previousValues"):
            if key in candidate and _contains_status_field(candidate[key]):
                return True
    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, nested_value in value.items():
            if _is_status_field(key):
                return True
            if _contains_status_field(nested_value):
                return True
        return False

    if isinstance(value, str):
        return _is_status_field(value)

    if _is_sequence(value):
        return any(_contains_status_field(item) for item in value)

    return False


def _is_status_field(value: Any) -> bool:
    label = _normalize_label(value)
    return label in _STATUS_FIELD_NAMES


def _extract_new_status(event: Mapping[str, Any]) -> Any:
    for candidate in _mapping_candidates(event):
        for key in _NEW_STATUS_KEYS:
            if key in candidate:
                return _coerce_status_value(candidate[key])

    for candidate in _mapping_candidates(event):
        for key in _CURRENT_STATUS_KEYS:
            if key in candidate:
                return _coerce_status_value(candidate[key])

    return None


def _coerce_status_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        for key in ("name", "title", "label", "to", "after", "new", "status", "state"):
            if key in value:
                return _coerce_status_value(value[key])
    return value


def _extract_first_text(event: Mapping[str, Any], keys: Sequence[str]) -> str | None:
    for candidate in _mapping_candidates(event):
        for key in keys:
            if key in candidate:
                value = candidate[key]
                if isinstance(value, str) and value.strip():
                    return value
    return None


def _mapping_candidates(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    candidates: list[Mapping[str, Any]] = []
    queue: deque[Any] = deque([event])

    while queue:
        value = queue.popleft()
        if isinstance(value, Mapping):
            candidates.append(value)
            for nested_value in value.values():
                if isinstance(nested_value, Mapping) or _is_sequence(nested_value):
                    queue.append(nested_value)
        elif _is_sequence(value):
            queue.extend(value)

    return candidates


def _is_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))


def _normalize_label(value: Any) -> str:
    if value is None:
        return ""

    text = str(value).strip()
    if not text:
        return ""

    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
