"""Build title update actions for Linear issues entering research.

The module is intentionally side-effect free: callers can decide how to apply
the returned action to Linear after the webhook payload has been evaluated.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELDS = {"status", "state", "workflowstate"}
_NEW_STATUS_KEYS = {
    "newstatus",
    "newstate",
    "newworkflowstate",
}
_TRIGGER_KEYS = {"trigger", "webhooktype", "action", "type"}
_DIRECT_STATUS_TRIGGERS = {"statuschanged", "statuschange", "statechanged", "workflowstatechanged"}
_GENERIC_UPDATE_TRIGGERS = {"update", "updated", "issueupdated", "updatedissue"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title-update action when an issue moves to "to research".

    The returned structure is small and serializable so it can be handed to the
    automation layer that performs the actual Linear mutation.
    """

    if not isinstance(event, Mapping):
        return None

    payload = _select_payload(event)
    if not _is_status_change(payload):
        return None

    status = _target_status(payload)
    if _normalize_label(status) != TARGET_STATUS:
        return None

    issue_id = _first_text(payload, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_text(payload, ("title", "name"))
    if not issue_id or not title:
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": _prefixed_title(title),
    }


def _select_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}

    for key in ("triggerContext", "trigger_context"):
        value = event.get(key)
        if isinstance(value, Mapping):
            payload.update(_issue_payload(value))

    automation_info = event.get("automation_trigger_info") or event.get("automationTriggerInfo")
    if isinstance(automation_info, Mapping):
        for key in ("triggerContext", "trigger_context"):
            value = automation_info.get(key)
            if isinstance(value, Mapping):
                payload.update(_issue_payload(value))

    payload.update(_issue_payload(event))
    return payload


def _issue_payload(source: Mapping[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}

    data = source.get("data")
    if isinstance(data, Mapping):
        payload.update(_issue_payload(data))

    issue = source.get("issue")
    if isinstance(issue, Mapping):
        payload.update(_issue_payload(issue))

    for key, value in source.items():
        if key not in {"data", "issue"}:
            payload[key] = value

    return payload


def _is_status_change(payload: Mapping[str, Any]) -> bool:
    trigger_values = {
        _normalize_token(value)
        for key, value in payload.items()
        if _normalize_key(key) in _TRIGGER_KEYS and isinstance(value, str)
    }

    if trigger_values & _DIRECT_STATUS_TRIGGERS:
        return True

    if trigger_values & _GENERIC_UPDATE_TRIGGERS:
        return _status_field_was_updated(payload)

    # Cursor's normalized status_changed trigger can arrive without an action
    # field in tests or manual invocations.
    return bool(_target_status(payload) and _status_field_was_updated(payload))


def _status_field_was_updated(payload: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields"):
        value = payload.get(key)
        if _contains_status_field(value):
            return True

    for key in ("changes", "changed", "updatedFrom", "updated_from", "previous"):
        value = payload.get(key)
        if _contains_status_field(value):
            return True

    return any(_normalize_key(key) in _NEW_STATUS_KEYS for key in payload)


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_key(value) in _STATUS_FIELDS

    if isinstance(value, Mapping):
        return any(_normalize_key(key) in _STATUS_FIELDS or _contains_status_field(nested) for key, nested in value.items())

    if isinstance(value, (list, tuple, set)):
        return any(_contains_status_field(item) for item in value)

    return False


def _target_status(payload: Mapping[str, Any]) -> str | None:
    for key in ("newStatus", "new_status", "newState", "new_state", "newWorkflowState", "new_workflow_state"):
        value = _status_name(payload.get(key))
        if value:
            return value

    for key in ("changes", "changed"):
        value = _status_from_change_payload(payload.get(key))
        if value:
            return value

    for key in ("status", "state", "workflowState", "workflow_state"):
        value = _status_name(payload.get(key))
        if value:
            return value

    return None


def _status_from_change_payload(value: Any) -> str | None:
    if not isinstance(value, Mapping):
        return None

    for field, change in value.items():
        if _normalize_key(field) not in _STATUS_FIELDS:
            continue

        if isinstance(change, Mapping):
            for key in ("to", "new", "newValue", "new_value", "after", "name"):
                status = _status_name(change.get(key))
                if status:
                    return status
        else:
            status = _status_name(change)
            if status:
                return status

    return None


def _status_name(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "status", "state", "workflowState", "workflow_state"):
            status = _status_name(value.get(key))
            if status:
                return status

    return None


def _first_text(payload: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _prefixed_title(title: str) -> str:
    stripped = title.strip()
    if stripped.lower().startswith(TITLE_PREFIX.lower()):
        return stripped
    return f"{TITLE_PREFIX}: {stripped}"


def _normalize_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def _normalize_token(value: Any) -> str:
    return _normalize_key(_normalize_label(value))


def _normalize_label(value: Any) -> str:
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", str(value))
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 2

    action = build_issue_title_update(event)
    print(json.dumps(action, sort_keys=True) if action else "null")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
