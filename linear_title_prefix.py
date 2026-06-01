"""Build title update actions for Linear issue status-change automation."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to research."""

    if not isinstance(event, Mapping):
        return None

    context = _event_context(event)
    if not _is_status_change(context):
        return None

    new_status = _new_status(context)
    if _normalize_text(new_status) != TARGET_STATUS:
        return None

    issue_id = _first_string(context, ("id", "issueId", "issue_id", "identifier"))
    title = _first_string(context, ("title", "name"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if not title or _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _event_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten the payload shapes used by Cursor and Linear webhooks."""

    context: dict[str, Any] = {}

    for key in ("issue", "data", "triggerContext"):
        value = event.get(key)
        if isinstance(value, Mapping):
            context.update(_event_context(value))

    state = event.get("state")
    if isinstance(state, Mapping):
        context["state"] = state

    workflow_state = event.get("workflowState") or event.get("workflow_state")
    if isinstance(workflow_state, Mapping):
        context["workflowState"] = workflow_state

    context.update(event)
    return context


def _is_status_change(context: Mapping[str, Any]) -> bool:
    for key in ("trigger", "webhookType", "action", "type"):
        value = context.get(key)
        normalized = _normalize_text(value)
        if normalized in {"status changed", "status change", "statuschanged"}:
            return True
        if normalized in {"issue updated", "updated issue", "update", "updated"}:
            return _updated_fields_include_status(context)

    return _updated_fields_include_status(context)


def _updated_fields_include_status(context: Mapping[str, Any]) -> bool:
    updated_fields = (
        context.get("updatedFields")
        or context.get("updated_fields")
        or context.get("changedFields")
        or context.get("changed_fields")
    )
    if isinstance(updated_fields, str):
        values = [updated_fields]
    elif isinstance(updated_fields, Mapping):
        values = updated_fields.keys()
    elif isinstance(updated_fields, list | tuple | set):
        values = updated_fields
    else:
        return False

    return any(_normalize_field_name(value) in STATUS_FIELDS for value in values)


def _new_status(context: Mapping[str, Any]) -> str | None:
    explicit_status = _first_string(
        context,
        (
            "newStatus",
            "new_status",
            "statusName",
            "status_name",
            "stateName",
            "state_name",
            "workflowStateName",
            "workflow_state_name",
        ),
    )
    if explicit_status:
        return explicit_status

    for key in ("status", "state", "workflowState", "workflow_state"):
        value = context.get(key)
        if isinstance(value, Mapping):
            nested_status = _first_string(value, ("name", "title", "status"))
            if nested_status:
                return nested_status
        elif isinstance(value, str):
            return value

    return None


def _first_string(context: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = context.get(key)
        if isinstance(value, str):
            return value
    return None


def _has_prefix(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())


def _normalize_field_name(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", _normalize_text(value))


def _normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    spaced = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", value)
    return re.sub(r"[\s_-]+", " ", spaced).strip().casefold()


def main() -> int:
    payload = json.load(sys.stdin)
    result = build_issue_title_update(payload)
    if result is not None:
        print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
