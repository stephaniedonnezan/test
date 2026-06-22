"""Build Linear issue title updates for research status transitions.

The automation receives slightly different payload shapes depending on whether
it is invoked by Cursor's flattened trigger context or Linear's nested webhook
body. This module keeps the status/title decision pure so it can be tested and
used by a small stdin JSON CLI.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_EVENT_KEYS = (
    "trigger",
    "webhookType",
    "webhook_type",
    "action",
    "type",
    "event",
    "eventType",
    "event_type",
)
_STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow state"}
_EXPLICIT_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "newWorkflowState",
    "new_workflow_state",
    "statusName",
    "status_name",
    "stateName",
    "state_name",
)
_CURRENT_STATUS_KEYS = ("status", "state", "workflowState", "workflow_state")
_UPDATED_FIELD_KEYS = (
    "updatedFields",
    "updated_fields",
    "changedFields",
    "changed_fields",
)
_CHANGES_KEYS = ("changes", "changed", "updated")
_ISSUE_ID_KEYS = ("issueId", "issue_id", "id", "identifier", "key")
_TITLE_KEYS = ("title", "issueTitle", "issue_title", "name")


def build_issue_title_update(event: Mapping[str, Any] | Any) -> dict[str, str] | None:
    """Return a title-update action when a Linear issue enters To Research.

    The returned dictionary is intentionally transport-agnostic:
    ``{"action": "update_issue_title", "issueId": "...", "title": "..."}``.
    Callers can translate it into the Linear API mutation they use.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    new_status = _first_status_value(event)
    if _normalize(new_status) != TARGET_STATUS:
        return None

    issue_id = _first_text(event, _ISSUE_ID_KEYS)
    title = _first_text(event, _TITLE_KEYS)
    if not issue_id or not title:
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": _prefixed_title(title),
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    event_names = {_normalize(value) for value in _event_values(event)}
    if "status changed" in event_names or "status change" in event_names:
        return True

    is_update = bool(
        event_names
        & {
            "update",
            "updated",
            "issue update",
            "issue updated",
            "updated issue",
        }
    )
    return is_update and _has_status_update_marker(event)


def _event_values(event: Mapping[str, Any]) -> Iterable[Any]:
    for candidate in _payload_contexts(event):
        for key in _EVENT_KEYS:
            if key in candidate:
                yield candidate[key]


def _has_status_update_marker(event: Mapping[str, Any]) -> bool:
    for candidate in _payload_contexts(event):
        for key in _UPDATED_FIELD_KEYS:
            value = candidate.get(key)
            if _contains_status_field_name(value):
                return True

        for key in _CHANGES_KEYS:
            changes = candidate.get(key)
            if isinstance(changes, Mapping):
                if any(_is_status_field_name(field) for field in changes):
                    return True
            elif _contains_status_field_name(changes):
                return True

    return False


def _first_status_value(event: Mapping[str, Any]) -> Any:
    candidates = list(_payload_contexts(event))

    for candidate in candidates:
        for key in _EXPLICIT_STATUS_KEYS:
            if key in candidate:
                return _name_or_text(candidate[key])

    for candidate in candidates:
        for key in _CHANGES_KEYS:
            value = _status_from_changes(candidate.get(key))
            if value is not None:
                return value

    for candidate in candidates:
        for key in _CURRENT_STATUS_KEYS:
            if key in candidate:
                return _name_or_text(candidate[key])

    return None


def _status_from_changes(changes: Any) -> Any:
    if not isinstance(changes, Mapping):
        return None

    for field_name, change in changes.items():
        if not _is_status_field_name(field_name):
            continue

        if isinstance(change, Mapping):
            for key in ("new", "to", "after", "value", "name"):
                if key in change:
                    return _name_or_text(change[key])
        return _name_or_text(change)

    return None


def _payload_contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely metadata/issue objects, preferring flatter trigger contexts."""

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        yield trigger_context

    automation_info = event.get("automation_trigger_info")
    if isinstance(automation_info, Mapping):
        nested_trigger_context = automation_info.get("triggerContext")
        if isinstance(nested_trigger_context, Mapping):
            yield nested_trigger_context

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            yield issue

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        yield issue

    if isinstance(data, Mapping):
        yield data

    yield event


def _contains_status_field_name(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(_is_status_field_name(key) for key in value)

    if isinstance(value, str):
        return _is_status_field_name(value)

    if isinstance(value, Iterable):
        return any(_contains_status_field_name(item) for item in value)

    return False


def _is_status_field_name(value: Any) -> bool:
    return _normalize(value) in _STATUS_FIELD_NAMES


def _first_text(event: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for candidate in _payload_contexts(event):
        for key in keys:
            if key not in candidate:
                continue

            value = _name_or_text(candidate[key])
            if isinstance(value, str):
                value = value.strip()
            if value:
                return str(value)

    return None


def _prefixed_title(title: str) -> str:
    title = title.strip()
    if title.lower().startswith(TITLE_PREFIX.lower()):
        return title
    return f"{TITLE_PREFIX}: {title}"


def _name_or_text(value: Any) -> Any:
    if isinstance(value, Mapping):
        for key in ("name", "title", "value"):
            if key in value:
                return _name_or_text(value[key])
    return value


def _normalize(value: Any) -> str:
    value = _name_or_text(value)
    if value is None:
        return ""

    text = str(value).strip()
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


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
