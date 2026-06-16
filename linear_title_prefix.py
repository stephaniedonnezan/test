"""Build Linear issue title updates for research-status automation.

The Cursor automation runtime can feed either a flat ``triggerContext`` payload
or a more direct Linear webhook payload. This module keeps the decision logic
small and deterministic so the caller can perform the actual Linear update.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow state"}
STATUS_EVENT_NAMES = {
    "status changed",
    "statuschange",
    "status changed issue",
    "issue status changed",
    "workflow state changed",
    "state changed",
}
GENERIC_UPDATE_EVENT_NAMES = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to To Research.

    The return value is intentionally side-effect free:
    ``{"action": "update_issue_title", "issueId": "...", "title": "..."}``.
    ``None`` means the payload does not need a title update.
    """

    if not isinstance(event, Mapping):
        return None

    payload = _merge_payload_context(event)
    if not _is_status_change_event(payload):
        return None

    status = _changed_status_name(payload)
    if _normalize_status(status) != TARGET_STATUS:
        return None

    issue_id = _issue_id(payload)
    title = _issue_title(payload)
    if not issue_id or not title:
        return None

    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _merge_payload_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten common automation and Linear webhook wrappers into one mapping."""

    merged: dict[str, Any] = {}

    for key in ("issue", "data", "triggerContext"):
        nested = event.get(key)
        if isinstance(nested, Mapping):
            merged.update(_merge_payload_context(nested))

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            merged.update(_merge_payload_context(issue))

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        merged.update(_merge_payload_context(issue))

    merged.update(event)
    return merged


def _is_status_change_event(payload: Mapping[str, Any]) -> bool:
    event_names = {
        _normalize_event_name(payload.get(key))
        for key in ("trigger", "webhookType", "action", "type", "event", "eventType")
    }
    event_names.discard("")

    if event_names & STATUS_EVENT_NAMES:
        return True

    if event_names & GENERIC_UPDATE_EVENT_NAMES:
        return _mentions_status_field(payload)

    # Cursor test harnesses sometimes provide only the newStatus and issue data.
    return bool(_changed_status_name(payload)) and _mentions_status_field(payload)


def _mentions_status_field(payload: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updatedFieldIds", "changedFields"):
        if _sequence_mentions_status(payload.get(key)):
            return True

    for key in ("changes", "updatedFrom", "previousValues"):
        value = payload.get(key)
        if isinstance(value, Mapping) and any(_is_status_field_name(name) for name in value):
            return True

    return any(key in payload for key in ("newStatus", "new_status", "status", "state", "workflowState"))


def _sequence_mentions_status(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field_name(value)

    if not isinstance(value, Sequence) or isinstance(value, (bytes, bytearray)):
        return False

    for item in value:
        if isinstance(item, Mapping):
            names = (item.get("name"), item.get("field"), item.get("fieldName"), item.get("id"))
            if any(_is_status_field_name(name) for name in names):
                return True
        elif _is_status_field_name(item):
            return True

    return False


def _changed_status_name(payload: Mapping[str, Any]) -> str | None:
    for key in ("newStatus", "new_status", "statusName", "stateName", "workflowStateName"):
        value = _string_value(payload.get(key))
        if value:
            return value

    for container_key in ("changes", "updatedFrom"):
        value = _status_from_change_container(payload.get(container_key))
        if value:
            return value

    for key in ("status", "state", "workflowState"):
        value = _name_or_string(payload.get(key))
        if value:
            return value

    return None


def _status_from_change_container(value: Any) -> str | None:
    if not isinstance(value, Mapping):
        return None

    for field_name, change in value.items():
        if not _is_status_field_name(field_name):
            continue

        if isinstance(change, Mapping):
            for key in ("to", "new", "newValue", "after", "name"):
                candidate = _name_or_string(change.get(key))
                if candidate:
                    return candidate
        else:
            candidate = _name_or_string(change)
            if candidate:
                return candidate

    return None


def _issue_id(payload: Mapping[str, Any]) -> str | None:
    for key in ("issueId", "issue_id", "identifier", "key", "id"):
        value = _string_value(payload.get(key))
        if value:
            return value
    return None


def _issue_title(payload: Mapping[str, Any]) -> str | None:
    for key in ("title", "name"):
        value = _string_value(payload.get(key))
        if value:
            return value
    return None


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())


def _name_or_string(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            nested = _string_value(value.get(key))
            if nested:
                return nested
        return None

    return _string_value(value)


def _string_value(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _is_status_field_name(value: Any) -> bool:
    normalized = _normalize_event_name(value)
    return normalized in STATUS_FIELD_NAMES


def _normalize_status(value: str | None) -> str:
    return _normalize_words(value)


def _normalize_event_name(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return _normalize_words(value)


def _normalize_words(value: str | None) -> str:
    if not value:
        return ""

    camel_spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value.strip())
    return re.sub(r"[^a-z0-9]+", " ", camel_spaced.casefold()).strip()


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON input: {exc}", file=sys.stderr)
        return 1

    if not isinstance(event, Mapping):
        return 0

    update = build_issue_title_update(event)
    if update:
        print(json.dumps(update, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
