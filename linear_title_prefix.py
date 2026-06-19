"""Build Linear issue title updates for Cursor research automation events."""

from __future__ import annotations

import json
import re
import sys
from typing import Any


RESEARCH_STATUS = "to research"
TITLE_PREFIX = "Cursor researching"
TITLE_PREFIX_SEPARATOR = f"{TITLE_PREFIX}: "

_STATUS_CHANGE_FIELDS = {"status", "state", "workflowstate", "workflow_state"}


def build_issue_title_update(event: dict[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update when an issue moves to "To Research".

    The Cursor automation payload contains a flat ``triggerContext`` object,
    while direct Linear webhooks usually put issue details under ``data`` or
    ``data.issue``. This helper accepts both shapes and only produces an update
    for status-change events that newly target ``To Research``.
    """

    if not isinstance(event, dict):
        return None

    trigger = _trigger_context(event)
    issue = _issue_payload(event, trigger)

    if not _is_status_change_event(event, trigger):
        return None

    new_status = _new_status(event, trigger, issue)
    if _normalize_status(new_status) != RESEARCH_STATUS:
        return None

    issue_id = _first_non_empty_string(
        trigger.get("id"),
        issue.get("identifier"),
        issue.get("id"),
        _nested_get(issue, ("issue", "identifier")),
        _nested_get(issue, ("issue", "id")),
    )
    title = _first_non_empty_string(
        trigger.get("title"),
        issue.get("title"),
        _nested_get(issue, ("issue", "title")),
    )

    if not issue_id or not title:
        return None

    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX_SEPARATOR}{title}",
    }


def _trigger_context(event: dict[str, Any]) -> dict[str, Any]:
    trigger = event.get("triggerContext")
    if isinstance(trigger, dict):
        return trigger

    automation_trigger = event.get("automation_trigger_info")
    if isinstance(automation_trigger, dict):
        trigger = automation_trigger.get("triggerContext")
        if isinstance(trigger, dict):
            return trigger

    return event


def _issue_payload(event: dict[str, Any], trigger: dict[str, Any]) -> dict[str, Any]:
    data = event.get("data")
    if isinstance(data, dict):
        issue = data.get("issue")
        if isinstance(issue, dict):
            return issue
        return data

    issue = event.get("issue")
    if isinstance(issue, dict):
        return issue

    return trigger


def _is_status_change_event(event: dict[str, Any], trigger: dict[str, Any]) -> bool:
    trigger_type = _first_non_empty_string(
        trigger.get("triggerType"),
        trigger.get("webhookType"),
        trigger.get("type"),
        event.get("type"),
        event.get("action"),
    )
    normalized_trigger = _normalize_event_type(trigger_type)
    if normalized_trigger in {"status_changed", "statuschanged"}:
        return True
    if normalized_trigger in {"issueupdated", "issue_update", "updated"}:
        return _has_status_change_marker(event)

    return _has_status_change_marker(event)


def _has_status_change_marker(event: dict[str, Any]) -> bool:
    updated_from = event.get("updatedFrom")
    if isinstance(updated_from, dict) and _contains_status_field(updated_from):
        return True

    changed_fields = event.get("changedFields")
    if isinstance(changed_fields, list) and any(
        _normalize_field_name(field) in _STATUS_CHANGE_FIELDS for field in changed_fields
    ):
        return True

    changes = event.get("changes")
    if isinstance(changes, dict) and _contains_status_field(changes):
        return True

    return False


def _new_status(
    event: dict[str, Any],
    trigger: dict[str, Any],
    issue: dict[str, Any],
) -> Any:
    return _first_present(
        trigger.get("newStatus"),
        trigger.get("status"),
        _nested_get(trigger, ("state", "name")),
        _nested_get(trigger, ("workflowState", "name")),
        _nested_get(event, ("data", "state", "name")),
        _nested_get(event, ("data", "workflowState", "name")),
        _nested_get(issue, ("state", "name")),
        _nested_get(issue, ("workflowState", "name")),
        issue.get("status"),
        issue.get("state"),
        issue.get("workflowState"),
    )


def _contains_status_field(fields: dict[str, Any]) -> bool:
    return any(_normalize_field_name(field) in _STATUS_CHANGE_FIELDS for field in fields)


def _normalize_status(value: Any) -> str:
    if isinstance(value, dict):
        value = _first_present(value.get("name"), value.get("label"), value.get("status"))
    if value is None:
        return ""
    normalized = re.sub(r"[_-]+", " ", str(value)).strip().lower()
    return re.sub(r"\s+", " ", normalized)


def _normalize_event_type(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().replace("-", "_").lower()


def _normalize_field_name(value: Any) -> str:
    return str(value).replace("-", "").replace("_", "").lower()


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(TITLE_PREFIX.casefold())


def _first_present(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def _first_non_empty_string(*values: Any) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _nested_get(payload: dict[str, Any], path: tuple[str, ...]) -> Any:
    value: Any = payload
    for key in path:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def main() -> int:
    """Read a JSON event from stdin and print the computed title update."""

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
