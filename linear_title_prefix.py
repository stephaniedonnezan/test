"""Build Linear issue title updates for research-status automations."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
TITLE_UPDATE_ACTION = "update_issue_title"


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update when a Linear issue moves to the research status.

    The automation payload may arrive as a flat trigger context or as a nested
    webhook body. This function normalizes the common shapes and keeps the
    behavior idempotent by skipping titles that already start with the prefix.
    """

    if not isinstance(event, Mapping):
        return None

    context = _event_context(event)
    if not _is_status_change_event(context):
        return None

    status = _get_status(context)
    if _normalize_label(status) != TARGET_STATUS:
        return None

    issue_id = _first_text(
        context,
        "id",
        "issueId",
        "issue_id",
        "identifier",
    )
    title = _first_text(context, "title", "name")

    if issue_id is None or title is None:
        return None

    title = title.strip()
    if not title or title.lower().startswith(TITLE_PREFIX.lower()):
        return None

    return {
        "action": TITLE_UPDATE_ACTION,
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def handle_issue_status_changed(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Compatibility alias for automation entrypoints named as event handlers."""

    return build_issue_title_update(event)


def _event_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten the common Linear automation/webhook containers into one context."""

    context: dict[str, Any] = {}

    for key in ("issue", "data", "triggerContext"):
        nested = event.get(key)
        if isinstance(nested, Mapping):
            context.update(_event_context(nested))

    state = event.get("state")
    if isinstance(state, Mapping):
        context.setdefault("status", state.get("name"))

    workflow_state = event.get("workflowState")
    if isinstance(workflow_state, Mapping):
        context.setdefault("status", workflow_state.get("name"))

    context.update(event)
    return context


def _is_status_change_event(context: Mapping[str, Any]) -> bool:
    normalized_triggers = {
        normalized
        for key in ("trigger", "webhookType", "action", "type")
        if (normalized := _normalize_label(context.get(key))) is not None
    }
    status_change_triggers = {
        "status changed",
        "status change",
        "state changed",
        "workflow state changed",
    }
    if normalized_triggers.intersection(status_change_triggers):
        return True

    if normalized_triggers.intersection({"issue updated", "updated issue"}):
        return _updated_fields_include_status(context.get("updatedFields"))

    return False


def _get_status(context: Mapping[str, Any]) -> Any:
    for key in ("newStatus", "new_status", "status"):
        value = context.get(key)
        if value is not None:
            return value

    state = context.get("state")
    if isinstance(state, Mapping):
        return state.get("name")

    workflow_state = context.get("workflowState")
    if isinstance(workflow_state, Mapping):
        return workflow_state.get("name")

    return None


def _updated_fields_include_status(updated_fields: Any) -> bool:
    if updated_fields is None:
        return False

    if isinstance(updated_fields, str):
        fields = [updated_fields]
    elif isinstance(updated_fields, Mapping):
        fields = updated_fields.keys()
    elif isinstance(updated_fields, Sequence):
        fields = updated_fields
    else:
        return False

    return any(
        _normalize_label(field) in {"status", "state", "workflow state"}
        for field in fields
        if isinstance(field, str)
    )


def _first_text(context: Mapping[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = context.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _normalize_label(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    spaced = re.sub(r"[^A-Za-z0-9]+", " ", spaced)
    return " ".join(spaced.lower().split())
