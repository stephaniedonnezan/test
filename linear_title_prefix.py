"""Build Linear issue title updates for research status changes.

The Cursor automation receives slightly different payload shapes depending on
whether it is triggered by Linear directly or by an automation wrapper. This
module keeps the decision small and explicit: only issue status changes into
"to research" produce a title update, and existing prefixes are left untouched.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {"status", "state", "workflow state", "workflow status"}
_TRIGGER_KEYS = {"trigger", "webhookType", "action", "type", "eventType", "webhook_type"}
_TITLE_KEYS = ("title", "name", "summary")
_ISSUE_ID_KEYS = ("id", "issueId", "issue_id", "identifier", "key")
_EXPLICIT_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "statusName",
    "status_name",
    "stateName",
    "state_name",
    "workflowStateName",
    "workflow_state_name",
)


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title-update action when a status changes to research.

    The returned action is intentionally transport-agnostic so the caller can
    map it to the actual Linear mutation layer.
    """

    if not isinstance(event, Mapping):
        return None

    payload = _flatten_event(event)
    if not _is_status_change_event(payload):
        return None

    status = _extract_status(payload)
    if _normalize_label(status) != _normalize_label(TARGET_STATUS):
        return None

    title = _extract_first_string(payload, _TITLE_KEYS)
    issue_id = _extract_first_string(payload, _ISSUE_ID_KEYS)
    if not title or not issue_id:
        return None

    stripped_title = title.strip()
    if _has_research_prefix(stripped_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {stripped_title}",
    }


def _flatten_event(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common nested payload containers without losing outer metadata."""

    flattened: dict[str, Any] = {}
    for container_key in ("triggerContext", "webhook", "payload", "data", "issue"):
        container = event.get(container_key)
        if isinstance(container, Mapping):
            flattened.update(_flatten_event(container))

    flattened.update(event)

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            flattened.update(issue)
            flattened.update({key: value for key, value in data.items() if key != "issue"})
            flattened.update(event)

    return flattened


def _is_status_change_event(payload: Mapping[str, Any]) -> bool:
    trigger_values = [
        value
        for key, value in payload.items()
        if key in _TRIGGER_KEYS and isinstance(value, str)
    ]

    if any(_is_direct_status_change(value) for value in trigger_values):
        return True

    changed_fields = _extract_changed_fields(payload)
    if changed_fields and any(_is_status_field(field) for field in changed_fields):
        return True

    return any(_looks_like_issue_update(value) for value in trigger_values) and any(
        key in payload for key in (*_EXPLICIT_STATUS_KEYS, "status", "state", "workflowState")
    )


def _extract_changed_fields(payload: Mapping[str, Any]) -> list[str]:
    field_values: list[str] = []
    for key in ("updatedFields", "changedFields", "updated_fields", "changed_fields"):
        value = payload.get(key)
        if isinstance(value, str):
            field_values.append(value)
        elif isinstance(value, Iterable) and not isinstance(value, (str, bytes, Mapping)):
            field_values.extend(str(item) for item in value)

    return field_values


def _extract_status(payload: Mapping[str, Any]) -> str | None:
    for key in _EXPLICIT_STATUS_KEYS:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value

    for key in ("state", "workflowState", "status"):
        value = payload.get(key)
        if isinstance(value, Mapping):
            nested_name = value.get("name")
            if isinstance(nested_name, str) and nested_name.strip():
                return nested_name
        elif isinstance(value, str) and value.strip():
            return value

    return None


def _extract_first_string(payload: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value

    for container_key in ("issue", "data", "triggerContext"):
        container = payload.get(container_key)
        if isinstance(container, Mapping):
            nested = _extract_first_string(container, keys)
            if nested:
                return nested

    return None


def _normalize_label(value: str | None) -> str:
    if not value:
        return ""

    words = re.sub(r"([a-z])([A-Z])", r"\1 \2", value.strip())
    words = re.sub(r"[^a-zA-Z0-9]+", " ", words)
    return " ".join(words.casefold().split())


def _is_direct_status_change(value: str) -> bool:
    normalized = _normalize_label(value)
    return normalized in {"status changed", "status change", "state changed", "workflow state changed"}


def _looks_like_issue_update(value: str) -> bool:
    normalized = _normalize_label(value)
    return normalized in {"issue updated", "updated issue", "update", "updated"}


def _is_status_field(value: str) -> bool:
    return _normalize_label(value) in _STATUS_FIELD_NAMES


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(TITLE_PREFIX.casefold())


def main() -> int:
    payload = json.load(sys.stdin)
    update = build_issue_title_update(payload)
    if update is not None:
        print(json.dumps(update))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
