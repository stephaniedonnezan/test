"""Build Linear issue title updates for research status transitions.

The automation receives Linear webhook-style payloads from Cursor triggers.  When
an issue status changes to "to research", this module returns the title update
that prefixes the issue with "Cursor researching".
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}
STATUS_TRIGGER_VALUES = {
    "status changed",
    "statuschanged",
    "state changed",
    "statechanged",
    "workflow state changed",
    "workflowstatechanged",
    "workflow status changed",
    "workflowstatuschanged",
}
GENERIC_UPDATE_VALUES = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue enters research status."""

    if not isinstance(event, Mapping):
        return None

    context = _event_context(event)
    if not _is_status_change_event(event, context):
        return None

    status = _extract_new_status(context)
    if _normalize_text(status) != TARGET_STATUS:
        return None

    issue_id = _extract_first_text(context, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _extract_first_text(context, ("title", "name"))
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


def _event_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common wrapper shapes so top-level trigger data wins."""

    context: dict[str, Any] = {}

    for key in ("triggerContext", "data"):
        value = event.get(key)
        if isinstance(value, Mapping):
            context.update(_issue_data(value))
            context.update(value)

    context.update(_issue_data(event))
    context.update(event)
    return context


def _issue_data(payload: Mapping[str, Any]) -> dict[str, Any]:
    issue = payload.get("issue")
    if isinstance(issue, Mapping):
        return dict(issue)
    return {}


def _is_status_change_event(event: Mapping[str, Any], context: Mapping[str, Any]) -> bool:
    event_values = _event_type_values(event, context)
    if any(value in STATUS_TRIGGER_VALUES for value in event_values):
        return True

    if any(value in GENERIC_UPDATE_VALUES for value in event_values):
        return _updated_fields_include_status(event, context) or _changes_include_status(event, context)

    return False


def _event_type_values(event: Mapping[str, Any], context: Mapping[str, Any]) -> set[str]:
    values: set[str] = set()
    for payload in (event, context):
        for key in ("trigger", "webhookType", "action", "type"):
            value = payload.get(key)
            if isinstance(value, str):
                values.add(_normalize_text(value))
                values.add(_normalize_identifier(value))
    return values


def _updated_fields_include_status(event: Mapping[str, Any], context: Mapping[str, Any]) -> bool:
    fields = _collect_iterable_values(event, context, ("updatedFields", "updated_fields"))
    return any(_normalize_field_name(field) in STATUS_FIELDS for field in fields)


def _changes_include_status(event: Mapping[str, Any], context: Mapping[str, Any]) -> bool:
    for payload in (event, context):
        changes = payload.get("changes")
        if isinstance(changes, Mapping):
            return any(_normalize_field_name(field) in STATUS_FIELDS for field in changes)
    return False


def _collect_iterable_values(
    event: Mapping[str, Any],
    context: Mapping[str, Any],
    keys: tuple[str, ...],
) -> list[Any]:
    values: list[Any] = []
    for payload in (event, context):
        for key in keys:
            value = payload.get(key)
            if isinstance(value, str):
                values.append(value)
            elif isinstance(value, Iterable) and not isinstance(value, (bytes, Mapping)):
                values.extend(value)
    return values


def _extract_new_status(context: Mapping[str, Any]) -> str | None:
    for key in ("newStatus", "new_status", "statusName", "stateName", "workflowStateName"):
        value = context.get(key)
        text = _as_text(value)
        if text:
            return text

    for key in ("status", "state", "workflowState", "workflow_state"):
        value = context.get(key)
        text = _as_text(value)
        if text:
            return text

    return None


def _extract_first_text(context: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        text = _as_text(context.get(key))
        if text:
            return text
    return None


def _as_text(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, Mapping):
        for key in ("name", "title", "identifier", "key", "id"):
            text = _as_text(value.get(key))
            if text:
                return text
    return None


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    normalized = re.sub(r"[_\-/]+", " ", spaced)
    normalized = re.sub(r"\s+", " ", normalized).strip().lower()
    return normalized or None


def _normalize_identifier(value: str) -> str | None:
    normalized = re.sub(r"[^a-z0-9]+", "", value.lower())
    return normalized or None


def _normalize_field_name(value: Any) -> str | None:
    text = _as_text(value)
    if text is None:
        return None
    return _normalize_identifier(text)


def main() -> int:
    """Read a JSON event from stdin and print the generated action, if any."""

    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
