"""Build Linear issue title updates for issues moved to research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


RESEARCH_PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow_state"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title-update action when a Linear issue moves to research.

    The Cursor automation payload is intentionally accepted in both the flat
    triggerContext shape and the nested Linear webhook shape so this handler can
    be used directly in tests or wired into a webhook runner.
    """

    if not isinstance(event, Mapping):
        return None

    payload = _flatten_payload(event)
    if not _is_status_change_event(payload):
        return None

    status = _extract_new_status(payload)
    if _normalize_value(status) != _normalize_value(RESEARCH_STATUS):
        return None

    title = _extract_text(payload, ("title", "issueTitle", "name", "summary"))
    issue_id = _extract_text(payload, ("issueId", "issue_id", "identifier", "key", "id"))
    if not title or not issue_id:
        return None

    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{RESEARCH_PREFIX}: {title}",
    }


def _flatten_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}

    def merge(value: Any) -> None:
        if isinstance(value, Mapping):
            payload.update(value)

    # Merge broad context first and issue details later, then let outer fields
    # win so explicit automation metadata is not shadowed by nested issue data.
    for key in ("triggerContext", "webhook", "data"):
        value = event.get(key)
        merge(value)
        if isinstance(value, Mapping):
            for nested_key in ("issue", "node", "state", "workflowState"):
                nested = value.get(nested_key)
                if isinstance(nested, Mapping):
                    for nested_value_key, nested_value in nested.items():
                        payload.setdefault(nested_value_key, nested_value)
                    if nested_key in ("state", "workflowState"):
                        payload.setdefault(nested_key, nested)

    for key in ("issue", "node"):
        value = event.get(key)
        if isinstance(value, Mapping):
            for nested_key, nested_value in value.items():
                payload.setdefault(nested_key, nested_value)

    payload.update(event)
    return payload


def _is_status_change_event(payload: Mapping[str, Any]) -> bool:
    event_names = [
        payload.get(key)
        for key in ("trigger", "webhookType", "action", "type", "eventType")
        if payload.get(key) is not None
    ]
    normalized_events = {_normalize_value(name) for name in event_names}

    if any(name in {"status changed", "status change"} for name in normalized_events):
        return True

    if any(name in {"issue updated", "updated issue", "update"} for name in normalized_events):
        return _has_status_update_marker(payload)

    return False


def _has_status_update_marker(payload: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        fields = payload.get(key)
        if _contains_status_field(fields):
            return True

    changes = payload.get("changes") or payload.get("changed")
    if isinstance(changes, Mapping):
        return any(_is_status_field(key) for key in changes)

    return False


def _contains_status_field(fields: Any) -> bool:
    if isinstance(fields, str):
        return _is_status_field(fields)

    if isinstance(fields, Sequence) and not isinstance(fields, (bytes, bytearray, str)):
        return any(_is_status_field(field) for field in fields)

    return False


def _is_status_field(value: Any) -> bool:
    if not isinstance(value, str):
        return False

    return re.sub(r"[^a-z0-9]", "", _split_camel_case(value).lower()) in STATUS_FIELD_NAMES


def _extract_new_status(payload: Mapping[str, Any]) -> str | None:
    for key in ("newStatus", "new_status", "statusName", "status_name"):
        value = _string_from_value(payload.get(key))
        if value:
            return value

    changes = payload.get("changes") or payload.get("changed")
    if isinstance(changes, Mapping):
        for key, change in changes.items():
            if _is_status_field(key):
                value = _extract_change_value(change)
                if value:
                    return value

    for key in ("status", "state", "workflowState", "workflow_state"):
        value = _string_from_value(payload.get(key))
        if value:
            return value

    return None


def _extract_change_value(change: Any) -> str | None:
    if isinstance(change, Mapping):
        for key in ("newValue", "new_value", "to", "after", "name"):
            value = _string_from_value(change.get(key))
            if value:
                return value
    return _string_from_value(change)


def _extract_text(payload: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _string_from_value(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            nested = value.get(key)
            if isinstance(nested, str) and nested.strip():
                return nested.strip()

    return None


def _has_research_prefix(title: str) -> bool:
    return title.strip().lower().startswith(RESEARCH_PREFIX.lower())


def _normalize_value(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    spaced = _split_camel_case(value)
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", spaced.lower())).strip()


def _split_camel_case(value: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
