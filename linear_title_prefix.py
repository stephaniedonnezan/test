"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "state name",
    "state id",
    "workflow state",
    "workflow state name",
    "workflow state id",
}
_STATUS_CHANGE_EVENTS = {
    "status changed",
    "status change",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
}
_ISSUE_UPDATE_EVENTS = {
    "issue updated",
    "updated issue",
    "update issue",
    "issue update",
    "update",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update action when an issue enters "to research".

    The automation runtime can pass a flattened trigger context, while Linear
    webhooks are often nested under ``data.issue``. This function accepts both
    shapes and returns a small side-effect-free action for the caller to apply.
    """

    if not isinstance(event, Mapping):
        return None

    context = _issue_context(event)
    if not _is_status_change_to_research(event, context):
        return None

    issue_id = _first_text(
        context,
        (
            "identifier",
            "key",
            "issueId",
            "issue_id",
            "issueID",
            "id",
        ),
    )
    title = _first_text(context, ("title", "issueTitle", "issue_title", "name"))

    if not issue_id or not title:
        return None
    if title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _is_status_change_to_research(
    event: Mapping[str, Any], context: Mapping[str, Any]
) -> bool:
    if not _is_status_change_event(event):
        return False

    status = _new_status(event, context)
    return _normalize(status) == TARGET_STATUS


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    event_values = [
        value
        for payload in _iter_mappings(event)
        for key, value in payload.items()
        if _normalize(key) in {"trigger", "type", "action", "webhook type", "event"}
    ]

    normalized_values = {_normalize(value) for value in event_values}
    if normalized_values & _STATUS_CHANGE_EVENTS:
        return True

    if normalized_values & _ISSUE_UPDATE_EVENTS:
        return _updated_status_fields(event)

    return False


def _new_status(event: Mapping[str, Any], context: Mapping[str, Any]) -> str | None:
    explicit_status = _first_text(
        context,
        (
            "newStatus",
            "new_status",
            "newState",
            "new_state",
            "newWorkflowState",
            "new_workflow_state",
            "statusName",
            "stateName",
            "workflowStateName",
        ),
    )
    if explicit_status:
        return explicit_status

    for key in ("status", "state", "workflowState", "workflow_state"):
        value = context.get(key)
        if isinstance(value, Mapping):
            nested_name = _first_text(value, ("name", "title", "id"))
            if nested_name:
                return nested_name
        elif isinstance(value, str) and value.strip():
            return value.strip()

    changed_status = _changed_field_status(event)
    if changed_status:
        return changed_status

    return None


def _issue_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common nesting levels, with outer trigger metadata taking priority."""

    context: dict[str, Any] = {}

    for key in ("issue", "data", "triggerContext"):
        value = event.get(key)
        if isinstance(value, Mapping):
            context.update(value)

            nested_issue = value.get("issue")
            if isinstance(nested_issue, Mapping):
                context.update(nested_issue)

            nested_data = value.get("data")
            if isinstance(nested_data, Mapping):
                context.update(nested_data)

    context.update(event)
    return context


def _updated_status_fields(event: Mapping[str, Any]) -> bool:
    for payload in _iter_mappings(event):
        updated_fields = payload.get("updatedFields")
        if _contains_status_field(updated_fields):
            return True

        updated_fields = payload.get("updated_fields")
        if _contains_status_field(updated_fields):
            return True

        changes = payload.get("changes")
        if isinstance(changes, Mapping):
            if any(_normalize(key) in _STATUS_FIELD_NAMES for key in changes):
                return True
        elif isinstance(changes, Iterable) and not isinstance(changes, (str, bytes)):
            if _contains_status_field(changes):
                return True

    return False


def _changed_field_status(event: Mapping[str, Any]) -> str | None:
    for payload in _iter_mappings(event):
        changes = payload.get("changes")
        if not isinstance(changes, Mapping):
            continue

        for key, value in changes.items():
            if _normalize(key) not in _STATUS_FIELD_NAMES:
                continue
            if isinstance(value, Mapping):
                after = value.get("to") or value.get("after") or value.get("new")
                if isinstance(after, Mapping):
                    return _first_text(after, ("name", "title", "id"))
                if isinstance(after, str) and after.strip():
                    return after.strip()
            elif isinstance(value, str) and value.strip():
                return value.strip()

    return None


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize(value) in _STATUS_FIELD_NAMES

    if isinstance(value, Mapping):
        return any(_normalize(key) in _STATUS_FIELD_NAMES for key in value)

    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        return any(_contains_status_field(item) for item in value)

    return False


def _iter_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for nested_value in value.values():
            yield from _iter_mappings(nested_value)
    elif isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        for nested_value in value:
            yield from _iter_mappings(nested_value)


def _first_text(payload: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _normalize(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    value = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    value = re.sub(r"[^A-Za-z0-9]+", " ", value)
    return " ".join(value.lower().split())


def main() -> int:
    event = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(event), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
