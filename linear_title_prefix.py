"""Build Linear issue title updates for issues entering research."""

from __future__ import annotations

import json
import re
import sys
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {
    "status",
    "state",
    "stateid",
    "workflowstate",
    "workflowstateid",
}
STATUS_CHANGE_TRIGGERS = {
    "status_changed",
    "status changed",
    "state_changed",
    "state changed",
    "workflow_state_changed",
    "workflow state changed",
}
EXPLICIT_NON_STATUS_TRIGGERS = {
    "comment",
    "comment_created",
    "comment created",
    "comment_updated",
    "comment updated",
}


def build_issue_title_update(event: dict[str, Any]) -> dict[str, str] | None:
    """Return a title-update action when a Linear issue moves to research.

    The automation can receive either the Cursor Cloud trigger wrapper or a
    Linear-like webhook payload, so the extraction below accepts several common
    locations while still requiring a status-change signal.
    """

    if not isinstance(event, dict):
        return None

    contexts = _candidate_contexts(event)
    if not any(_is_status_change_event(context) for context in contexts):
        return None

    new_status = _first_text(_status_candidates(contexts))
    if _normalize_status(new_status) != TARGET_STATUS:
        return None

    title = _first_text(_title_candidates(contexts))
    issue_id = _first_text(_issue_id_candidates(contexts))
    if not title or not issue_id:
        return None

    title = title.strip()
    if _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _candidate_contexts(event: dict[str, Any]) -> list[dict[str, Any]]:
    contexts: list[dict[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, dict) and all(value is not existing for existing in contexts):
            contexts.append(value)

    add(event)
    trigger_info = event.get("automation_trigger_info")
    if isinstance(trigger_info, dict):
        add(trigger_info)
        add(trigger_info.get("triggerContext"))
    add(event.get("triggerContext"))

    data = event.get("data")
    if isinstance(data, dict):
        add(data)
        add(data.get("issue"))

    add(event.get("issue"))
    return contexts


def _is_status_change_event(context: dict[str, Any]) -> bool:
    trigger = _normalize_label(_first_text(_trigger_candidates(context)))
    if trigger in EXPLICIT_NON_STATUS_TRIGGERS:
        return False
    if trigger in STATUS_CHANGE_TRIGGERS:
        return True

    return _changed_fields_include_status(context)


def _trigger_candidates(context: dict[str, Any]) -> list[Any]:
    return [
        context.get("trigger"),
        context.get("webhookType"),
        context.get("webhook_type"),
        context.get("event"),
        context.get("eventType"),
        context.get("type"),
    ]


def _changed_fields_include_status(context: dict[str, Any]) -> bool:
    for key in ("changedFields", "updatedFields"):
        fields = context.get(key)
        if isinstance(fields, list) and any(_is_status_field(field) for field in fields):
            return True

    changes = context.get("changes")
    if isinstance(changes, dict) and any(_is_status_field(field) for field in changes):
        return True

    updated_from = context.get("updatedFrom")
    if isinstance(updated_from, dict) and any(_is_status_field(field) for field in updated_from):
        return True

    return False


def _status_candidates(contexts: list[dict[str, Any]]) -> list[Any]:
    values: list[Any] = []
    for context in contexts:
        values.extend(
            [
                context.get("newStatus"),
                context.get("new_status"),
                context.get("statusName"),
                context.get("stateName"),
                context.get("workflowStateName"),
                context.get("status"),
                context.get("state"),
                context.get("workflowState"),
            ]
        )
        values.extend(_change_new_values(context.get("changes")))
    return values


def _change_new_values(changes: Any) -> list[Any]:
    if not isinstance(changes, dict):
        return []

    values: list[Any] = []
    for field, value in changes.items():
        if not _is_status_field(field):
            continue
        if isinstance(value, dict):
            values.extend(
                [
                    value.get("new"),
                    value.get("newValue"),
                    value.get("to"),
                    value.get("after"),
                    value.get("name"),
                ]
            )
        else:
            values.append(value)
    return values


def _title_candidates(contexts: list[dict[str, Any]]) -> list[Any]:
    values: list[Any] = []
    for context in contexts:
        values.append(context.get("title"))
        data = context.get("data")
        if isinstance(data, dict):
            values.append(data.get("title"))
        issue = context.get("issue")
        if isinstance(issue, dict):
            values.append(issue.get("title"))
    return values


def _issue_id_candidates(contexts: list[dict[str, Any]]) -> list[Any]:
    values: list[Any] = []
    for context in contexts:
        values.extend([context.get("issueId"), context.get("issueID"), context.get("id"), context.get("identifier")])
        data = context.get("data")
        if isinstance(data, dict):
            values.extend([data.get("issueId"), data.get("issueID"), data.get("id"), data.get("identifier")])
        issue = context.get("issue")
        if isinstance(issue, dict):
            values.extend([issue.get("issueId"), issue.get("issueID"), issue.get("id"), issue.get("identifier")])
    return values


def _first_text(values: list[Any]) -> str | None:
    for value in values:
        text = _text_value(value)
        if text:
            return text
    return None


def _text_value(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, dict):
        for key in ("name", "title", "id", "identifier"):
            text = _text_value(value.get(key))
            if text:
                return text
    return None


def _normalize_status(value: str | None) -> str | None:
    if value is None:
        return None
    return _normalize_label(value)


def _normalize_label(value: str | None) -> str | None:
    if value is None:
        return None
    words = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    words = re.sub(r"[^A-Za-z0-9]+", " ", words).strip().lower()
    return re.sub(r"\s+", " ", words) or None


def _is_status_field(value: Any) -> bool:
    text = _text_value(value)
    if text is None:
        return False
    return _normalize_label(text).replace(" ", "") in STATUS_FIELD_NAMES


def _has_prefix(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 2

    action = build_issue_title_update(event)
    if action:
        print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
