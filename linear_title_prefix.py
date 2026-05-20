"""Build Linear issue title updates for research status transitions."""

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
    """Return a title update action when an issue moves to "to research"."""
    if not isinstance(event, Mapping):
        return None

    context = _issue_context(event)
    if not _is_status_changed_event(event, context):
        return None

    status = _new_status(event, context)
    if _normalize_status(status) != TARGET_STATUS:
        return None

    issue_id = _first_text(context, ("id", "issueId", "issue_id", "identifier"))
    title = _first_text(context, ("title", "name"))
    if not issue_id or not title:
        return None

    if title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _issue_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge the common Linear issue payload containers into one lookup map."""
    context: dict[str, Any] = {}

    for key in ("issue", "data", "triggerContext"):
        value = event.get(key)
        if isinstance(value, Mapping):
            context.update(value)

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            context.update(issue)

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        issue = trigger_context.get("issue")
        if isinstance(issue, Mapping):
            context.update(issue)
        context.update(trigger_context)

    context.update(event)
    return context


def _is_status_changed_event(
    event: Mapping[str, Any], context: Mapping[str, Any]
) -> bool:
    trigger_values = _event_type_values(event, context)
    normalized_values = {_normalize_event_type(value) for value in trigger_values}

    if "statuschanged" in normalized_values or "statuschange" in normalized_values:
        return True

    if "issueupdated" in normalized_values or "update" in normalized_values:
        return _updated_fields_include_status(event, context)

    return False


def _event_type_values(
    event: Mapping[str, Any], context: Mapping[str, Any]
) -> list[Any]:
    values: list[Any] = []
    for source in (event, event.get("triggerContext"), event.get("data"), context):
        if not isinstance(source, Mapping):
            continue
        for key in ("trigger", "webhookType", "action", "type"):
            if key in source:
                values.append(source[key])
    return values


def _updated_fields_include_status(
    event: Mapping[str, Any], context: Mapping[str, Any]
) -> bool:
    for source in (event, event.get("triggerContext"), event.get("data"), context):
        if not isinstance(source, Mapping):
            continue
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            fields = source.get(key)
            if isinstance(fields, str):
                fields = [fields]
            if isinstance(fields, (list, tuple, set)):
                for field in fields:
                    if _normalize_event_type(field) in STATUS_FIELDS:
                        return True
    return False


def _new_status(event: Mapping[str, Any], context: Mapping[str, Any]) -> Any:
    explicit_status = _first_value(
        (event, event.get("triggerContext"), event.get("data"), context),
        ("newStatus", "new_status", "statusName", "status_name"),
    )
    if explicit_status is not None:
        return explicit_status

    for key in ("state", "workflowState", "workflow_state", "status"):
        value = context.get(key)
        if isinstance(value, Mapping):
            name = value.get("name")
            if name is not None:
                return name

    return context.get("status")


def _first_text(source: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = source.get(key)
        if isinstance(value, str):
            stripped = value.strip()
            if stripped:
                return stripped
    return None


def _first_value(sources: tuple[Any, ...], keys: tuple[str, ...]) -> Any:
    for source in sources:
        if not isinstance(source, Mapping):
            continue
        for key in keys:
            if key in source and source[key] is not None:
                return source[key]
    return None


def _normalize_status(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    spaced = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", value)
    return re.sub(r"[\s_-]+", " ", spaced).strip().lower()


def _normalize_event_type(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def main() -> int:
    event = json.load(sys.stdin)
    result = build_issue_title_update(event)
    if result is not None:
        print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
