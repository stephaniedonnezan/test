"""Helpers for preparing Linear issue title updates from webhook events.

The automation only emits an update when an issue moves to the "to research"
status.  It keeps the output intentionally small so downstream workflow steps
can decide how to apply the update to Linear.
"""

from __future__ import annotations

import json
import re
import sys
from typing import Any, Mapping


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_CHANGED_TRIGGERS = {
    "status_changed",
    "statusChanged",
    "status_change",
}
STATUS_FIELD_NAMES = {"status", "state", "workflowState", "workflow_state"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Build a Linear title-update action for a relevant status-change event.

    Supported payloads include Cursor automation trigger contexts, flat events,
    and common nested Linear webhook shapes.  Returns ``None`` when the event
    does not represent an issue moving to "to research" or when the title is
    already prefixed.
    """

    payload = _payload(event)
    if not _is_status_change(payload):
        return None

    new_status = _new_status(payload)
    if _normalize_status(new_status) != TARGET_STATUS:
        return None

    issue = _issue(payload)
    issue_id = _first_string(issue, "issueId", "issue_id", "id", "identifier", "key")
    title = _first_string(issue, "title", "name")

    if not issue_id or not title or _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _payload(event: Mapping[str, Any]) -> Mapping[str, Any]:
    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        return trigger_context
    return event


def _is_status_change(payload: Mapping[str, Any]) -> bool:
    for key in ("webhookType", "trigger", "type", "action"):
        trigger = _first_string(payload, key)
        if trigger in STATUS_CHANGED_TRIGGERS:
            return True

    updated_fields = payload.get("updatedFields")
    if _contains_status_field(updated_fields):
        return True

    changes = payload.get("changes")
    if isinstance(changes, Mapping) and any(key in changes for key in STATUS_FIELD_NAMES):
        return True

    # Linear update events commonly use action="update" and put field changes
    # under updatedFrom or changes.  Treat these as status changes only when a
    # status-like field is explicitly present.
    updated_from = payload.get("updatedFrom")
    return isinstance(updated_from, Mapping) and any(
        key in updated_from for key in STATUS_FIELD_NAMES
    )


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return value in STATUS_FIELD_NAMES
    if isinstance(value, list):
        return any(_contains_status_field(item) for item in value)
    if isinstance(value, Mapping):
        return any(key in STATUS_FIELD_NAMES for key in value)
    return False


def _new_status(payload: Mapping[str, Any]) -> str | None:
    direct = _first_string(payload, "newStatus", "new_status", "toStatus")
    if direct:
        return direct

    for key in STATUS_FIELD_NAMES:
        value = payload.get(key)
        status = _status_name(value)
        if status:
            return status

    for container_name in ("changes", "updatedFrom"):
        container = payload.get(container_name)
        if isinstance(container, Mapping):
            for key in STATUS_FIELD_NAMES:
                status = _changed_to_status(container.get(key))
                if status:
                    return status

    data = payload.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            for key in STATUS_FIELD_NAMES:
                status = _status_name(issue.get(key))
                if status:
                    return status

    return None


def _changed_to_status(value: Any) -> str | None:
    if isinstance(value, Mapping):
        return _first_string(value, "to", "new", "after", "name")
    return _status_name(value)


def _issue(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    data = payload.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            return issue

    issue = payload.get("issue")
    if isinstance(issue, Mapping):
        return issue

    return payload


def _status_name(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        return _first_string(value, "name", "title", "status")
    return None


def _first_string(mapping: Mapping[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, str):
            stripped = value.strip()
            if stripped:
                return stripped
    return None


def _normalize_status(status: str | None) -> str | None:
    if status is None:
        return None
    normalized = re.sub(r"[\s_-]+", " ", status.strip().lower())
    return normalized or None


def _has_prefix(title: str) -> bool:
    return title.strip().lower().startswith(TITLE_PREFIX.lower())


def main() -> int:
    event = json.load(sys.stdin)
    if not isinstance(event, Mapping):
        raise TypeError("Expected a JSON object event")

    update = build_issue_title_update(event)
    if update is None:
        return 0

    json.dump(update, sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
