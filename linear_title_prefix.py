"""Build title updates for Linear issues handled by Cursor automations."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


RESEARCH_STATUS = "to research"
RESEARCH_TITLE_PREFIX = "Cursor researching"

_STATUS_CHANGED_EVENT_NAMES = {
    "statuschanged",
    "statuschange",
    "issuestatuschanged",
    "statechanged",
    "workflowstatechanged",
}
_STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflowstatus"}
_NEW_STATUS_KEYS = (
    "newStatus",
    "toStatus",
    "targetStatus",
    "status",
    "newState",
    "toState",
    "targetState",
    "state",
    "workflowState",
)


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear issue title update action for research status changes.

    Cursor automation payloads can arrive either as a flat trigger context or
    nested Linear webhook data. The function intentionally returns a plain
    dictionary so callers can decide how to execute the resulting action.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    new_status = _extract_new_status(event)
    if _normalize_text(new_status) != RESEARCH_STATUS:
        return None

    issue = _extract_issue(event)
    issue_id = _extract_first_text(issue, ("id", "issueId")) or _extract_first_text(
        event, ("issueId",)
    )
    title = _extract_first_text(issue, ("title", "name"))

    if not issue_id or not title:
        return None

    if title.lower().startswith(RESEARCH_TITLE_PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{RESEARCH_TITLE_PREFIX}: {title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    contexts = list(_candidate_contexts(event))

    for context in contexts:
        for key in ("trigger", "event", "action", "type", "webhookType"):
            event_name = _extract_text(context.get(key))
            if _normalize_identifier(event_name) in _STATUS_CHANGED_EVENT_NAMES:
                return True

        changed_fields = _extract_changed_fields(context)
        if any(_normalize_identifier(field) in _STATUS_FIELD_NAMES for field in changed_fields):
            return True

    return False


def _extract_new_status(event: Mapping[str, Any]) -> str | None:
    for context in _candidate_contexts(event):
        status = _extract_first_text(context, _NEW_STATUS_KEYS)
        if status:
            return status

        changes = context.get("changes")
        if isinstance(changes, Mapping):
            status = _extract_status_from_changes(changes)
            if status:
                return status

        data = context.get("data")
        if isinstance(data, Mapping):
            status = _extract_status_from_changes(data)
            if status:
                return status

    issue = _extract_issue(event)
    return _extract_first_text(issue, ("status", "state", "workflowState"))


def _extract_status_from_changes(changes: Mapping[str, Any]) -> str | None:
    for key in ("status", "state", "workflowState"):
        value = changes.get(key)
        if isinstance(value, Mapping):
            status = _extract_first_text(value, ("to", "new", "name", "title"))
            if status:
                return status
        else:
            status = _extract_text(value)
            if status:
                return status

    return None


def _extract_issue(event: Mapping[str, Any]) -> Mapping[str, Any]:
    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            return issue

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        return issue

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        return trigger_context

    return event


def _candidate_contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    yield event

    for key in ("triggerContext", "data", "issue"):
        value = event.get(key)
        if isinstance(value, Mapping):
            yield value

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            yield issue


def _extract_changed_fields(context: Mapping[str, Any]) -> list[str]:
    fields: list[str] = []

    for key in ("changedFields", "updatedFields"):
        value = context.get(key)
        if isinstance(value, str):
            fields.append(value)
        elif isinstance(value, Iterable) and not isinstance(value, (bytes, str, Mapping)):
            fields.extend(_extract_text(item) for item in value)

    for key in ("updatedFrom", "previousValues"):
        value = context.get(key)
        if isinstance(value, Mapping):
            fields.extend(_extract_text(field) for field in value.keys())

    return [field for field in fields if field]


def _extract_first_text(context: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for key in keys:
        if key not in context:
            continue

        text = _extract_text(context[key])
        if text:
            return text

    return None


def _extract_text(value: Any) -> str | None:
    if value is None:
        return None

    if isinstance(value, str):
        text = value.strip()
        return text or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "label", "value", "id"):
            text = _extract_text(value.get(key))
            if text:
                return text
        return None

    return str(value).strip() or None


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""

    return re.sub(r"\s+", " ", value.replace("_", " ").replace("-", " ")).strip().lower()


def _normalize_identifier(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]", "", (value or "").lower())


def main() -> int:
    """Read a JSON event from stdin and print the title update action."""

    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    print(json.dumps(update))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
