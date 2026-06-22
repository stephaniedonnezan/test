"""Build Linear issue title updates for Cursor research status changes.

The handler is intentionally small and dependency-free so it can be used by
automation runners that pass either Cursor trigger contexts or Linear webhook
payloads over stdin.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
import json
import re
import sys
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_DIRECT_STATUS_CHANGE_EVENTS = {
    "statuschange",
    "statuschanged",
    "statechange",
    "statechanged",
    "workflowstatechange",
    "workflowstatechanged",
}
_GENERIC_UPDATE_EVENTS = {
    "update",
    "updated",
    "issueupdate",
    "issueupdated",
    "updatedissue",
}
_STATUS_FIELD_NAMES = {
    "status",
    "statusid",
    "state",
    "stateid",
    "workflowstate",
    "workflowstateid",
}
_EXPLICIT_NEW_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "newWorkflowState",
    "new_workflow_state",
    "toStatus",
    "to_status",
    "toState",
    "to_state",
    "statusName",
    "status_name",
    "stateName",
    "state_name",
    "workflowStateName",
    "workflow_state_name",
)
_STATUS_VALUE_KEYS = ("status", "state", "workflowState", "workflow_state")
_ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "key", "id")


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return an issue-title update action when an issue moves to research.

    The return value is deliberately declarative. The caller remains
    responsible for applying the update with the Linear API.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    new_status = _extract_new_status(event)
    if _normalize_token(new_status) != _normalize_token(TARGET_STATUS):
        return None

    issue = _extract_issue(event)
    if issue is None:
        return None

    issue_id, title = issue
    if _has_title_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    event_names = {
        _normalize_token(value)
        for payload in _iter_payload_mappings(event)
        for key in ("trigger", "webhookType", "action", "type")
        if (value := payload.get(key)) is not None
    }

    if event_names & _DIRECT_STATUS_CHANGE_EVENTS:
        return True

    if event_names & _GENERIC_UPDATE_EVENTS:
        return _status_field_changed(event)

    return False


def _status_field_changed(event: Mapping[str, Any]) -> bool:
    for payload in _iter_payload_mappings(event):
        if _field_list_contains_status(payload.get("updatedFields")):
            return True
        if _field_list_contains_status(payload.get("changedFields")):
            return True

        for key in ("changes", "updatedFrom", "updated_from", "previous"):
            value = payload.get(key)
            if isinstance(value, Mapping) and _mapping_mentions_status(value):
                return True

    return False


def _field_list_contains_status(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_token(value) in _STATUS_FIELD_NAMES

    if not isinstance(value, Iterable) or isinstance(value, (Mapping, bytes)):
        return False

    return any(_normalize_token(item) in _STATUS_FIELD_NAMES for item in value)


def _mapping_mentions_status(value: Mapping[str, Any]) -> bool:
    return any(_normalize_token(key) in _STATUS_FIELD_NAMES for key in value)


def _extract_new_status(event: Mapping[str, Any]) -> str | None:
    for payload in _iter_payload_mappings(event):
        for key in _EXPLICIT_NEW_STATUS_KEYS:
            status = _status_text(payload.get(key))
            if status:
                return status

    for payload in _iter_payload_mappings(event):
        status = _status_from_change_mapping(payload.get("changes"))
        if status:
            return status

    for payload in _iter_payload_mappings(event):
        for key in _STATUS_VALUE_KEYS:
            status = _status_text(payload.get(key))
            if status:
                return status

    return None


def _status_from_change_mapping(value: Any) -> str | None:
    if not isinstance(value, Mapping):
        return None

    for key, change in value.items():
        if _normalize_token(key) not in _STATUS_FIELD_NAMES:
            continue

        if isinstance(change, Mapping):
            for new_value_key in ("to", "new", "newValue", "after", "current", "name"):
                status = _status_text(change.get(new_value_key))
                if status:
                    return status
        else:
            status = _status_text(change)
            if status:
                return status

    return None


def _status_text(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "status", "state", "workflowState"):
            status = _status_text(value.get(key))
            if status:
                return status

    return None


def _extract_issue(event: Mapping[str, Any]) -> tuple[str, str] | None:
    for payload in _iter_issue_mappings(event):
        issue_id = _first_text_value(payload, _ISSUE_ID_KEYS)
        title = _first_text_value(payload, ("title",))
        if issue_id and title:
            return issue_id, title

    return None


def _first_text_value(payload: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _has_title_prefix(title: str) -> bool:
    return re.match(rf"^\s*{re.escape(TITLE_PREFIX)}\b", title, re.IGNORECASE) is not None


def _iter_issue_mappings(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    seen: set[int] = set()

    def emit(value: Any) -> Iterable[Mapping[str, Any]]:
        if isinstance(value, Mapping) and id(value) not in seen:
            seen.add(id(value))
            yield value

    yield from emit(event)
    yield from emit(_get_nested_mapping(event, ("automation_trigger_info", "triggerContext")))
    yield from emit(_get_nested_mapping(event, ("triggerContext",)))
    yield from emit(_get_nested_mapping(event, ("data", "issue")))
    yield from emit(_get_nested_mapping(event, ("payload", "issue")))
    yield from emit(_get_nested_mapping(event, ("issue",)))
    yield from emit(_get_nested_mapping(event, ("data",)))
    yield from emit(_get_nested_mapping(event, ("payload",)))

    for payload in _iter_payload_mappings(event):
        if payload.get("title") is not None and any(key in payload for key in _ISSUE_ID_KEYS):
            yield from emit(payload)


def _iter_payload_mappings(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    seen: set[int] = set()
    stack: list[Any] = [event]

    while stack:
        value = stack.pop(0)
        if not isinstance(value, Mapping) or id(value) in seen:
            continue

        seen.add(id(value))
        yield value

        for nested_key in ("automation_trigger_info", "triggerContext", "data", "issue", "payload"):
            nested = value.get(nested_key)
            if isinstance(nested, Mapping):
                stack.append(nested)

        for nested_key in ("changes", "updatedFrom", "updated_from"):
            nested = value.get(nested_key)
            if isinstance(nested, Mapping):
                stack.append(nested)


def _get_nested_mapping(payload: Mapping[str, Any], path: tuple[str, ...]) -> Mapping[str, Any] | None:
    value: Any = payload
    for key in path:
        if not isinstance(value, Mapping):
            return None
        value = value.get(key)
    return value if isinstance(value, Mapping) else None


def _normalize_token(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"[^a-z0-9]+", "", str(value).lower())


def main() -> None:
    payload = json.load(sys.stdin)
    update = build_issue_title_update(payload)
    if update is not None:
        print(json.dumps(update, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
