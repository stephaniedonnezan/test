"""Build title update actions for Linear issues moved to To Research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
TITLE_SEPARATOR = ": "

_STATUS_CHANGE_FIELDS = {
    "status",
    "statusid",
    "state",
    "stateid",
    "workflowstate",
    "workflowstateid",
}
_EXPLICIT_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "newStateName",
    "new_state_name",
    "newWorkflowState",
    "new_workflow_state",
    "statusName",
    "status_name",
    "stateName",
    "state_name",
    "workflowStateName",
    "workflow_state_name",
)
_FALLBACK_STATUS_KEYS = ("status", "state", "workflowState", "workflow_state")
_TITLE_KEYS = ("title", "issueTitle", "issue_title")
_ISSUE_ID_KEYS = ("id", "issueId", "issue_id", "identifier")
_EVENT_KEYS = ("trigger", "webhookType", "eventType", "action", "type")


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return an issue-title update action when a Linear issue enters To Research.

    The function accepts both the flat Cursor automation trigger payload shape and
    nested Linear webhook-like payloads. It is intentionally side-effect free so
    callers can decide how to apply the returned action.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = list(_candidate_contexts(event))
    if not _is_status_change_event(contexts):
        return None

    status = _first_status(contexts)
    if _normalize(status) != TARGET_STATUS:
        return None

    title = _first_string(contexts, _TITLE_KEYS)
    issue_id = _first_string(contexts, _ISSUE_ID_KEYS)
    if not title or not issue_id:
        return None

    trimmed_title = title.strip()
    if _has_prefix(trimmed_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}{TITLE_SEPARATOR}{trimmed_title}",
    }


def _candidate_contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield useful payload layers from outer trigger metadata to issue data."""

    yield event

    for key in ("triggerContext", "trigger_context", "data", "issue"):
        nested = event.get(key)
        if isinstance(nested, Mapping):
            yield nested

    for parent_key in ("triggerContext", "trigger_context", "data"):
        parent = event.get(parent_key)
        if not isinstance(parent, Mapping):
            continue
        for child_key in ("issue", "data"):
            child = parent.get(child_key)
            if isinstance(child, Mapping):
                yield child


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    context_list = list(contexts)

    for value in _field_values(context_list, _EVENT_KEYS):
        normalized = _normalize(value)
        if normalized in {
            "status changed",
            "status change",
            "state changed",
            "state change",
            "workflow state changed",
            "workflow state change",
            "issue status changed",
            "issue updated status",
        }:
            return True
        if (
            any(token in normalized.split() for token in ("status", "state", "workflow"))
            and any(token in normalized.split() for token in ("changed", "change"))
        ):
            return True

    if any(_normalize(value) in {"update", "updated", "issue updated", "updated issue"} for value in _field_values(context_list, _EVENT_KEYS)):
        return any(_updated_field_is_status_related(context) for context in context_list)

    return False


def _updated_field_is_status_related(context: Mapping[str, Any]) -> bool:
    updated_fields = context.get("updatedFields") or context.get("updated_fields")
    if isinstance(updated_fields, str):
        values: Iterable[Any] = re.split(r"[\s,]+", updated_fields)
    elif isinstance(updated_fields, Iterable) and not isinstance(updated_fields, Mapping):
        values = updated_fields
    else:
        values = ()

    for value in values:
        normalized = re.sub(r"[^a-z0-9]", "", _normalize(value))
        if normalized in _STATUS_CHANGE_FIELDS:
            return True
    return False


def _first_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    context_list = list(contexts)
    explicit = _first_string(context_list, _EXPLICIT_STATUS_KEYS)
    if explicit:
        return explicit

    return _first_string(context_list, _FALLBACK_STATUS_KEYS)


def _first_string(contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value
            if isinstance(value, Mapping):
                nested_name = value.get("name")
                if isinstance(nested_name, str) and nested_name.strip():
                    return nested_name
    return None


def _field_values(contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> Iterable[Any]:
    for context in contexts:
        for key in keys:
            if key in context:
                yield context[key]


def _normalize(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    spaced_camel_case = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    normalized = re.sub(r"[_\-\s]+", " ", spaced_camel_case).strip().lower()
    return normalized


def _has_prefix(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())


def main() -> int:
    """Read a JSON payload from stdin and print the title update action, if any."""

    payload = json.load(sys.stdin)
    action = build_issue_title_update(payload)
    if action is not None:
        print(json.dumps(action))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
