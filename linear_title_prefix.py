"""Build Linear issue title updates for research status changes.

The automation trigger sends JSON payloads for issue status changes. This
module keeps the decision logic small and testable: when an issue moves to
"To Research", return the title update payload that prefixes the title with
"Cursor researching".
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
ACTION = "update_issue_title"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflow state", "workflow status"}
STATUS_CHANGE_TRIGGERS = {
    "status changed",
    "status change",
    "statuschanged",
    "status_changed",
    "state changed",
    "state change",
    "statechanged",
    "state_changed",
    "workflow state changed",
    "workflow state change",
    "workflowstatechanged",
    "workflow_state_changed",
}
UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action for To Research status changes.

    The function accepts the flat Cursor automation trigger payload shape and
    common nested Linear webhook shapes. It returns ``None`` when the event does
    not represent a status change to "To Research" or the title is already
    prefixed.
    """

    if not isinstance(event, Mapping):
        return None

    payload = _event_payload(event)
    issue = _issue_payload(payload)
    merged = _merged_context(payload, issue)

    if not _is_status_change_event(payload, merged):
        return None

    if _normalize_status(_new_status(payload, issue, merged)) != TARGET_STATUS:
        return None

    issue_id = _first_string(
        issue,
        merged,
        keys=("issueId", "issue_id", "identifier", "key", "id"),
    )
    title = _first_string(issue, merged, keys=("title", "name", "summary"))
    if not issue_id or not title:
        return None

    if title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": ACTION,
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _event_payload(event: Mapping[str, Any]) -> Mapping[str, Any]:
    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        return trigger_context
    return event


def _issue_payload(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    data = payload.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            return issue
        if _looks_like_issue(data):
            return data

    issue = payload.get("issue")
    if isinstance(issue, Mapping):
        return issue

    return {}


def _looks_like_issue(value: Mapping[str, Any]) -> bool:
    return any(key in value for key in ("title", "identifier", "issueId", "issue_id"))


def _merged_context(
    payload: Mapping[str, Any], issue: Mapping[str, Any]
) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    data = payload.get("data")
    if isinstance(data, Mapping):
        merged.update(data)
    merged.update(issue)
    merged.update(payload)
    return merged


def _is_status_change_event(
    payload: Mapping[str, Any], merged: Mapping[str, Any]
) -> bool:
    event_names = list(_event_names(payload)) + list(_event_names(merged))
    normalized_names = {_normalize_name(name) for name in event_names}

    if normalized_names & STATUS_CHANGE_TRIGGERS:
        return True

    if normalized_names & UPDATE_TRIGGERS:
        return _changed_status_fields(payload, merged)

    return False


def _event_names(source: Mapping[str, Any]) -> Iterable[str]:
    for key in ("trigger", "webhookType", "action", "type", "eventType"):
        value = source.get(key)
        if isinstance(value, str):
            yield value


def _changed_status_fields(*sources: Mapping[str, Any]) -> bool:
    for source in sources:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            if _contains_status_field(source.get(key)):
                return True

        changes = source.get("changes")
        if isinstance(changes, Mapping):
            if any(_is_status_field(key) for key in changes):
                return True
        elif isinstance(changes, list):
            for change in changes:
                if isinstance(change, Mapping) and _contains_status_field(
                    change.get("field") or change.get("fieldName") or change.get("name")
                ):
                    return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)
    if isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray, Mapping)):
        return any(_contains_status_field(item) for item in value)
    return False


def _is_status_field(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    return _normalize_name(value) in STATUS_FIELDS


def _new_status(
    payload: Mapping[str, Any], issue: Mapping[str, Any], merged: Mapping[str, Any]
) -> Any:
    for source in (merged, payload):
        value = _first_value(
            source,
            keys=(
                "newStatus",
                "new_status",
                "toStatus",
                "to_status",
                "newState",
                "new_state",
                "statusName",
                "status_name",
                "stateName",
                "state_name",
                "workflowStateName",
                "workflow_state_name",
            ),
        )
        if value is not None:
            return value

    changed_value = _status_from_changes(payload) or _status_from_changes(merged)
    if changed_value is not None:
        return changed_value

    for source in (issue, merged):
        value = _first_value(source, keys=("status", "state", "workflowState"))
        if value is not None:
            return value

    return None


def _status_from_changes(source: Mapping[str, Any]) -> Any:
    changes = source.get("changes")
    if isinstance(changes, Mapping):
        for field, change in changes.items():
            if _is_status_field(field):
                return _change_destination(change)
    elif isinstance(changes, list):
        for change in changes:
            if not isinstance(change, Mapping):
                continue
            field = change.get("field") or change.get("fieldName") or change.get("name")
            if _contains_status_field(field):
                destination = _change_destination(change)
                if destination is not None:
                    return destination

    return None


def _change_destination(change: Any) -> Any:
    if isinstance(change, Mapping):
        return _first_value(
            change,
            keys=(
                "to",
                "toValue",
                "to_value",
                "newValue",
                "new_value",
                "after",
                "name",
            ),
        )
    return change


def _first_string(*sources: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    value = _first_value(*sources, keys=keys)
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _first_value(*sources: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    for source in sources:
        for key in keys:
            if key not in source:
                continue
            value = source[key]
            if isinstance(value, Mapping):
                nested = _first_value(value, keys=("name", "title", "identifier", "id"))
                if nested is not None:
                    return nested
            elif value is not None:
                return value
    return None


def _normalize_status(value: Any) -> str | None:
    if isinstance(value, Mapping):
        value = _first_value(value, keys=("name", "title", "status", "state"))
    if not isinstance(value, str):
        return None
    return _normalize_name(value)


def _normalize_name(value: str) -> str:
    value = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
