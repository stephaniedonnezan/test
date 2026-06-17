"""Build Linear issue title updates for research status changes.

The automation receives webhook-shaped payloads from Cursor/Linear.  When the
payload represents an issue moving to "to research", this module returns the
title update action expected by the surrounding automation runner.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_CAMEL_CASE_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_SEPARATORS = re.compile(r"[\s_-]+")

_DIRECT_STATUS_TRIGGERS = {
    "status changed",
    "status change",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
}

_ISSUE_UPDATE_TRIGGERS = {
    "issue updated",
    "updated issue",
    "issue update",
    "update issue",
    "update",
    "updated",
}

_STATUS_FIELD_TOKENS = {
    "status",
    "statusid",
    "state",
    "stateid",
    "workflowstate",
    "workflowstateid",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update action when a Linear issue enters "to research".

    The returned object is intentionally small and transport-agnostic:
    ``{"action": "update_issue_title", "issueId": "...", "title": "..."}``.
    ``None`` indicates that the payload should not update the issue title.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    status = _extract_status(event)
    if _normalize(status) != TARGET_STATUS:
        return None

    issue_id = _extract_text(event, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _extract_text(event, ("title", "issueTitle", "issue_title"))
    if not issue_id or not title:
        return None

    if title.casefold().startswith(TITLE_PREFIX.casefold()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    event_names = {
        _normalize(value)
        for mapping in _walk_mappings(event)
        for key in ("trigger", "webhookType", "action", "type", "eventType")
        if (value := mapping.get(key)) is not None
    }

    if any(name in _DIRECT_STATUS_TRIGGERS for name in event_names):
        return True

    if any(name in _ISSUE_UPDATE_TRIGGERS for name in event_names):
        return _has_status_update_marker(event)

    return False


def _has_status_update_marker(event: Mapping[str, Any]) -> bool:
    for mapping in _walk_mappings(event):
        for key in ("updatedFields", "changedFields"):
            if _contains_status_field(mapping.get(key)):
                return True

        for key in ("changes", "updatedFrom", "previousValues"):
            value = mapping.get(key)
            if isinstance(value, Mapping) and any(_is_status_field(field) for field in value):
                return True
            if _contains_status_field(value):
                return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)

    if isinstance(value, Mapping):
        if any(_is_status_field(field) for field in value):
            return True
        return any(_contains_status_field(item) for item in value.values())

    if isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray, str)):
        return any(_contains_status_field(item) for item in value)

    return False


def _is_status_field(value: Any) -> bool:
    token = re.sub(r"[\s_-]+", "", _normalize(value))
    return token in _STATUS_FIELD_TOKENS


def _extract_status(event: Mapping[str, Any]) -> str | None:
    explicit_status_keys = (
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
    fallback_status_keys = ("status", "state", "workflowState", "workflow_state")

    return _extract_named_text(event, explicit_status_keys) or _extract_named_text(
        event, fallback_status_keys
    )


def _extract_named_text(event: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for mapping in _walk_mappings(event):
        for key in keys:
            if key in mapping:
                value = _text_from_value(mapping[key])
                if value:
                    return value

    return None


def _extract_text(event: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for mapping in _walk_mappings(event):
        for key in keys:
            value = mapping.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                return str(value)

    return None


def _text_from_value(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()

    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            nested = value.get(key)
            if isinstance(nested, str) and nested.strip():
                return nested.strip()

    return None


def _walk_mappings(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return likely payload contexts from most to least specific."""

    visited: set[int] = set()
    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if not isinstance(value, Mapping):
            return
        marker = id(value)
        if marker in visited:
            return
        visited.add(marker)
        contexts.append(value)
        for key in ("triggerContext", "payload", "body", "data", "issue"):
            add(value.get(key))

    if isinstance(event.get("triggerContext"), Mapping):
        add(event["triggerContext"])
    add(event)

    return contexts


def _normalize(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, Mapping):
        value = value.get("name") or value.get("title") or value.get("label") or ""

    text = str(value).strip()
    text = _CAMEL_CASE_BOUNDARY.sub(" ", text)
    text = _SEPARATORS.sub(" ", text)
    return text.casefold()


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"invalid JSON payload: {exc}", file=sys.stderr)
        return 1

    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, indent=2, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
