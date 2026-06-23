"""Build Linear issue title updates for Cursor research automation.

The helper is intentionally side-effect free: callers pass a Linear/Cursor
event payload and receive the title update they should apply, or ``None`` when
no issue title should change.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
PREFIXED_TITLE = f"{PREFIX}: "
RESEARCH_STATUS = "to research"

_DIRECT_STATUS_CHANGE_TRIGGERS = {
    "issue status changed",
    "issue_status_changed",
    "issuestatuschanged",
    "status changed",
    "status_changed",
    "statuschanged",
}

_STATUS_FIELD_NAMES = {
    "state",
    "stateid",
    "status",
    "statusid",
    "workflowstate",
    "workflowstateid",
    "workflow_state",
    "workflow_state_id",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title-update action when an issue moved to To Research.

    The returned payload is deliberately small so different runners can map it
    to their own Linear client:

    ``{"action": "update_issue_title", "issueId": "...", "title": "..."}``
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    status = _extract_status(event)
    if _normalize_value(status) != RESEARCH_STATUS:
        return None

    issue_id = _extract_issue_id(event)
    title = _extract_title(event)
    if not issue_id or not issue_id.strip() or not title or not title.strip():
        return None

    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIXED_TITLE}{title.strip()}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    context = _mapping_at(event, "automation_trigger_info", "triggerContext")
    if context is None:
        context = _mapping_at(event, "triggerContext")

    trigger_values = [
        event.get("trigger"),
        event.get("triggerType"),
        event.get("webhookType"),
    ]
    if context is not None:
        trigger_values.extend(
            [
                context.get("trigger"),
                context.get("triggerType"),
                context.get("webhookType"),
            ]
        )

    if any(_normalize_value(value) in _DIRECT_STATUS_CHANGE_TRIGGERS for value in trigger_values):
        return True

    if _has_status_change_marker(event):
        return True

    return context is not None and _has_status_change_marker(context)


def _has_status_change_marker(payload: Mapping[str, Any]) -> bool:
    for key in ("changedFields", "updatedFields", "changed", "changes", "updatedFrom"):
        if _contains_status_field(payload.get(key)):
            return True

    data = payload.get("data")
    if isinstance(data, Mapping):
        return _has_status_change_marker(data)

    return False


def _contains_status_field(value: Any) -> bool:
    if value is None:
        return False

    if isinstance(value, str):
        return _field_name(value) in _STATUS_FIELD_NAMES

    if isinstance(value, Mapping):
        return any(
            _field_name(key) in _STATUS_FIELD_NAMES or _contains_status_field(item)
            for key, item in value.items()
        )

    if isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray)):
        return any(_contains_status_field(item) for item in value)

    return False


def _extract_status(event: Mapping[str, Any]) -> Any:
    context = _mapping_at(event, "automation_trigger_info", "triggerContext")
    if context is None:
        context = _mapping_at(event, "triggerContext")

    for source in (context, event):
        if source is None:
            continue
        status = _first_present(source, ("newStatus", "status", "state", "workflowState"))
        if status is not None:
            return status

    for path in (
        ("data", "state"),
        ("data", "status"),
        ("data", "workflowState"),
        ("data", "issue", "state"),
        ("data", "issue", "status"),
        ("data", "issue", "workflowState"),
        ("issue", "state"),
        ("issue", "status"),
        ("issue", "workflowState"),
    ):
        status = _value_at(event, *path)
        if status is not None:
            return status

    return None


def _extract_issue_id(event: Mapping[str, Any]) -> str | None:
    context = _mapping_at(event, "automation_trigger_info", "triggerContext")
    if context is None:
        context = _mapping_at(event, "triggerContext")

    for source in (context, event):
        if source is None:
            continue
        issue_id = _first_present(source, ("issueId", "id", "identifier"))
        if issue_id is not None:
            return str(issue_id)

    for path in (
        ("data", "issue", "id"),
        ("data", "id"),
        ("issue", "id"),
        ("data", "identifier"),
        ("issue", "identifier"),
    ):
        issue_id = _value_at(event, *path)
        if issue_id is not None:
            return str(issue_id)

    return None


def _extract_title(event: Mapping[str, Any]) -> str | None:
    context = _mapping_at(event, "automation_trigger_info", "triggerContext")
    if context is None:
        context = _mapping_at(event, "triggerContext")

    for source in (context, event):
        if source is None:
            continue
        title = source.get("title")
        if title is not None:
            return str(title)

    for path in (
        ("data", "issue", "title"),
        ("data", "title"),
        ("issue", "title"),
    ):
        title = _value_at(event, *path)
        if title is not None:
            return str(title)

    return None


def _has_research_prefix(title: str) -> bool:
    return title.strip().lower().startswith(PREFIX.lower())


def _first_present(source: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = source.get(key)
        if value is not None:
            return value
    return None


def _mapping_at(source: Mapping[str, Any], *path: str) -> Mapping[str, Any] | None:
    value = _value_at(source, *path)
    if isinstance(value, Mapping):
        return value
    return None


def _value_at(source: Mapping[str, Any], *path: str) -> Any:
    value: Any = source
    for key in path:
        if not isinstance(value, Mapping):
            return None
        value = value.get(key)
        if value is None:
            return None
    return value


def _normalize_value(value: Any) -> str:
    if isinstance(value, Mapping):
        value = _first_present(value, ("name", "title", "label", "value"))
    if value is None:
        return ""
    return " ".join(str(value).strip().lower().replace("_", " ").replace("-", " ").split())


def _field_name(value: Any) -> str:
    return str(value).strip().lower().replace("-", "_")


def main() -> int:
    """Read a JSON event from stdin and print the title update decision."""

    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 2

    result = build_issue_title_update(event)
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
