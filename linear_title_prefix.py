"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any


TITLE_PREFIX = "Cursor researching"
TITLE_PREFIX_WITH_SEPARATOR = f"{TITLE_PREFIX}: "
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update request when an issue moves to research."""
    if not isinstance(event, Mapping):
        return None

    context = _event_context(event)
    if not _is_status_change_event(context):
        return None

    status = _first_text(
        context,
        (
            "newStatus",
            "new_status",
            "status",
            "state.name",
            "workflowState.name",
            "workflow_state.name",
        ),
    )
    if _normalize_text(status) != _normalize_text(TARGET_STATUS):
        return None

    issue_id = _first_text(context, ("id", "issueId", "issue_id", "identifier"))
    title = _first_text(context, ("title", "name"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if not title or title.lower().startswith(TITLE_PREFIX.lower()):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX_WITH_SEPARATOR}{title}",
    }


def handle_issue_status_changed(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Compatibility wrapper for JS-style automation naming."""
    return build_issue_title_update(event)


def _event_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten common Linear webhook envelopes, with outer fields taking priority."""
    context: dict[str, Any] = {}

    data = event.get("data")
    if isinstance(data, Mapping):
        data_issue = data.get("issue")
        if isinstance(data_issue, Mapping):
            context.update(data_issue)
        context.update(data)

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        context.update(issue)

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        context.update(trigger_context)

    context.update(event)
    return context


def _is_status_change_event(context: Mapping[str, Any]) -> bool:
    event_names = (
        context.get("trigger"),
        context.get("webhookType"),
        context.get("action"),
        context.get("type"),
    )
    normalized_event_names = {_normalize_text(value) for value in event_names}
    if "status changed" in normalized_event_names or "statuschanged" in normalized_event_names:
        return True

    if "issue updated" not in normalized_event_names and "updated issue" not in normalized_event_names:
        return False

    return _updated_fields_include_status(context.get("updatedFields"))


def _updated_fields_include_status(updated_fields: Any) -> bool:
    if isinstance(updated_fields, str):
        fields = [updated_fields]
    elif isinstance(updated_fields, Sequence) and not isinstance(updated_fields, (bytes, bytearray)):
        fields = updated_fields
    else:
        return False

    return any(_normalize_text(field) in {"status", "state", "workflow state"} for field in fields)


def _first_text(context: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = _dig(context, key)
        if isinstance(value, str):
            stripped = value.strip()
            if stripped:
                return stripped
    return None


def _dig(context: Mapping[str, Any], dotted_key: str) -> Any:
    current: Any = context
    for part in dotted_key.split("."):
        if not isinstance(current, Mapping):
            return None
        current = current.get(part)
    return current


def _normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    value = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    value = re.sub(r"[^a-zA-Z0-9]+", " ", value)
    return " ".join(value.casefold().split())
