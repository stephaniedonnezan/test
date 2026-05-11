"""Build Linear issue-title updates for research status changes."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
PREFIXED_TITLE_TEMPLATE = f"{PREFIX}: {{title}}"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to research."""

    context = _event_context(event)
    if context is None:
        return None

    if not _is_status_change(context):
        return None

    if _normalized_status(_first_value(context, ("newStatus", "new_status", "status"))) != TARGET_STATUS:
        return None

    issue_id = _clean_string(_first_value(context, ("issueId", "issue_id", "identifier", "id")))
    title = _clean_string(_first_value(context, ("title", "name")))
    if issue_id is None or title is None:
        return None

    if _has_prefix(title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id,
        "title": PREFIXED_TITLE_TEMPLATE.format(title=title),
    }


def handle_issue_status_changed(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Compatibility alias for automation entrypoints."""

    return build_issue_title_update(event)


def _event_context(event: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(event, Mapping):
        return None

    context: dict[str, Any] = dict(event)
    for key in ("triggerContext", "data", "issue"):
        value = context.get(key)
        if isinstance(value, Mapping):
            context.update(value)

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            context.update(issue)

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        context.update(issue)

    for state_key in ("state", "workflowState"):
        state = context.get(state_key)
        if isinstance(state, Mapping) and "status" not in context:
            name = _clean_string(state.get("name"))
            if name is not None:
                context["status"] = name

    return context


def _is_status_change(context: Mapping[str, Any]) -> bool:
    trigger_values = [
        _normalized_token(context.get("trigger")),
        _normalized_token(context.get("action")),
        _normalized_token(context.get("type")),
    ]
    if any(value in {"statuschanged", "statechanged", "workflowstatechanged"} for value in trigger_values):
        return True

    webhook_type = _normalized_token(context.get("webhookType"))
    if webhook_type in {"statuschanged", "statechanged", "workflowstatechanged"}:
        return True

    if webhook_type in {"issueupdated", "updatedissue"} or any(
        value in {"issueupdated", "updatedissue"} for value in trigger_values
    ):
        return _updated_fields_include_status(context.get("updatedFields") or context.get("updated_fields"))

    return False


def _updated_fields_include_status(updated_fields: Any) -> bool:
    if isinstance(updated_fields, str):
        fields = [updated_fields]
    elif isinstance(updated_fields, Mapping):
        fields = updated_fields.keys()
    elif isinstance(updated_fields, list | tuple | set):
        fields = updated_fields
    else:
        return False

    status_fields = {"status", "state", "workflowstate", "workflowstatus"}
    return any(_normalized_token(field) in status_fields for field in fields)


def _first_value(context: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = context.get(key)
        if value is not None:
            return value
    return None


def _clean_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    stripped = value.strip()
    return stripped or None


def _has_prefix(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())


def _normalized_status(value: Any) -> str | None:
    text = _clean_string(value)
    if text is None:
        return None

    words = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    words = re.sub(r"[_\-\s]+", " ", words).strip().casefold()
    return words or None


def _normalized_token(value: Any) -> str | None:
    text = _clean_string(value)
    if text is None:
        return None

    words = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    normalized = re.sub(r"[^a-z0-9]+", "", words.casefold())
    return normalized or None
