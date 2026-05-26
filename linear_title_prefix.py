"""Build Linear issue title updates for Cursor research automation events."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}
STATUS_CHANGE_EVENTS = {"status changed", "status change", "statuschanged"}
ISSUE_UPDATE_EVENTS = {"issue updated", "updated issue", "update", "updated"}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear issue title update action when an issue enters research."""
    if not isinstance(event, Mapping):
        return None

    payload = _payload_view(event)

    if not _is_status_change_event(payload):
        return None

    status = _new_status(payload)
    if _normalize_text(status) != TARGET_STATUS:
        return None

    issue = _issue_view(payload)
    issue_id = _first_text(issue, ("id", "issueId", "issue_id", "identifier"))
    title = _first_text(issue, ("title", "name"))
    if issue_id is None or title is None:
        return None

    trimmed_title = title.strip()
    if not trimmed_title or _has_research_prefix(trimmed_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {trimmed_title}",
    }


def _payload_view(event: Mapping[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key in ("issue", "data", "triggerContext"):
        nested = event.get(key)
        if isinstance(nested, Mapping):
            payload.update(nested)

    for key, value in event.items():
        if key not in {"issue", "data", "triggerContext"}:
            payload[key] = value

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        payload.update(trigger_context)

    issue = _nested_mapping(event, ("data", "issue")) or _nested_mapping(event, ("issue",))
    if issue is not None:
        payload["issue"] = issue

    return payload


def _issue_view(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    issue = payload.get("issue")
    if isinstance(issue, Mapping):
        return issue

    data_issue = _nested_mapping(payload, ("data", "issue"))
    if data_issue is not None:
        return data_issue

    return payload


def _is_status_change_event(payload: Mapping[str, Any]) -> bool:
    normalized_events = {
        _normalize_text(value)
        for key in ("trigger", "webhookType", "action", "type")
        for value in (payload.get(key),)
        if isinstance(value, str)
    }

    if normalized_events & STATUS_CHANGE_EVENTS:
        return True

    if normalized_events & ISSUE_UPDATE_EVENTS:
        updated_fields = payload.get("updatedFields") or payload.get("updated_fields")
        if isinstance(updated_fields, Mapping):
            updated_fields = updated_fields.keys()
        if isinstance(updated_fields, (list, tuple, set)):
            return any(_normalize_field_name(field) in STATUS_FIELDS for field in updated_fields)

    return False


def _new_status(payload: Mapping[str, Any]) -> str | None:
    for key in ("newStatus", "new_status", "statusName", "stateName", "workflowStateName"):
        value = payload.get(key)
        if isinstance(value, str):
            return value

    for key in ("status", "state", "workflowState", "workflow_state"):
        value = payload.get(key)
        if isinstance(value, str):
            return value
        if isinstance(value, Mapping):
            name = value.get("name")
            if isinstance(name, str):
                return name

    issue = payload.get("issue")
    if isinstance(issue, Mapping):
        for key in ("status", "state", "workflowState", "workflow_state"):
            value = issue.get(key)
            if isinstance(value, str):
                return value
            if isinstance(value, Mapping):
                name = value.get("name")
                if isinstance(name, str):
                    return name

    return None


def _first_text(mapping: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _nested_mapping(mapping: Mapping[str, Any], path: tuple[str, ...]) -> Mapping[str, Any] | None:
    current: Any = mapping
    for key in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current if isinstance(current, Mapping) else None


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(TITLE_PREFIX.casefold())


def _normalize_field_name(value: Any) -> str:
    return re.sub(r"[\s_-]+", "", str(value)).casefold()


def _normalize_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return re.sub(r"[\s_-]+", " ", spaced).strip().casefold()


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        json.dump(update, sys.stdout)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
