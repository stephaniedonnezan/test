"""Build title updates for Linear issues moved into research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to research.

    The Cursor automation trigger exposes a compact ``triggerContext`` payload,
    while native Linear webhooks usually nest the issue under ``data``. This
    function accepts both shapes and returns a serializable action for callers
    that perform the actual Linear API update.
    """

    if not isinstance(event, Mapping):
        return None

    flattened = _flatten_event(event)
    if not _is_status_change(flattened):
        return None

    new_status = _extract_new_status(flattened)
    if _normalize_status(new_status) != _normalize_status(TARGET_STATUS):
        return None

    issue_id = _first_text(flattened, ("issueId", "issue_id", "id", "identifier"))
    title = _first_text(flattened, ("title", "name"))
    if not issue_id or not title:
        return None

    stripped_title = title.strip()
    if _has_prefix(stripped_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {stripped_title}",
    }


def handle_issue_status_changed(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Compatibility alias for callers that name the handler after the trigger."""

    return build_issue_title_update(event)


def _flatten_event(event: Mapping[str, Any]) -> dict[str, Any]:
    flattened: dict[str, Any] = {}

    for container_key in ("issue", "data", "triggerContext"):
        container = event.get(container_key)
        if isinstance(container, Mapping):
            flattened.update(_flatten_event(container))

    state = event.get("state")
    if isinstance(state, Mapping) and "status" not in flattened:
        flattened["status"] = state.get("name")

    workflow_state = event.get("workflowState")
    if isinstance(workflow_state, Mapping) and "status" not in flattened:
        flattened["status"] = workflow_state.get("name")

    status = event.get("status")
    if isinstance(status, Mapping) and "status" not in flattened:
        flattened["status"] = status.get("name")

    flattened.update(event)
    return flattened


def _is_status_change(flattened: Mapping[str, Any]) -> bool:
    trigger_values = _normalized_tokens(
        flattened.get(key) for key in ("trigger", "webhookType", "action", "type")
    )
    if trigger_values & {
        "statuschanged",
        "statuschange",
        "statuschangedissue",
        "statusupdated",
        "statechanged",
        "statechange",
        "stateupdated",
        "workflowstatechanged",
        "workflowstatechange",
        "workflowstateupdated",
    }:
        return True

    if trigger_values & {"update", "updated", "issueupdated", "updatedissue"}:
        return _has_status_field_change(flattened)

    return False


def _extract_new_status(flattened: Mapping[str, Any]) -> str | None:
    explicit = _first_text(
        flattened,
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
    if explicit:
        return explicit

    for key in ("status", "state", "workflowState"):
        value = flattened.get(key)
        if isinstance(value, Mapping):
            name = value.get("name")
            if isinstance(name, str):
                return name
        if isinstance(value, str):
            return value

    return None


def _has_status_field_change(flattened: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "changedFields", "changes", "updatedFrom"):
        if _updated_fields_include_status(flattened.get(key)):
            return True
    return False


def _updated_fields_include_status(updated_fields: Any) -> bool:
    if isinstance(updated_fields, str):
        return _normalize_token(updated_fields) in STATUS_FIELDS

    if isinstance(updated_fields, Mapping):
        return any(_normalize_token(key) in STATUS_FIELDS for key in updated_fields)

    if isinstance(updated_fields, Iterable):
        return any(_normalize_token(field) in STATUS_FIELDS for field in updated_fields)

    return False


def _normalized_tokens(values: Iterable[Any]) -> set[str]:
    return {_normalize_token(value) for value in values if isinstance(value, str)}


def _normalize_token(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    return re.sub(r"[^a-z0-9]+", "", spaced.lower())


def _normalize_status(value: str | None) -> str:
    return _normalize_token(value)


def _first_text(mapping: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def main() -> int:
    action = build_issue_title_update(json.load(sys.stdin))
    if action is not None:
        print(json.dumps(action))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
