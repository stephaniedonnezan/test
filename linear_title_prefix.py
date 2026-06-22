"""Build Linear issue title updates for research-status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


RESEARCH_STATUS = "to research"
TITLE_PREFIX = "Cursor researching"
STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow state"}
EXPLICIT_NEW_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "toStatus",
    "to_status",
    "newState",
    "new_state",
    "toState",
    "to_state",
    "newWorkflowState",
    "new_workflow_state",
)
STATUS_FALLBACK_KEYS = ("status", "state", "workflowState", "workflow_state")
ISSUE_ID_KEYS = ("issueId", "issue_id", "id", "identifier", "key")


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to research.

    The automation trigger payload can arrive as either a flat Cursor
    ``triggerContext`` object or a nested Linear webhook object. This function
    returns an explicit action for the caller to apply, and ``None`` when no
    title change is needed.
    """
    if not isinstance(event, Mapping):
        return None

    contexts = _candidate_contexts(event)
    if not contexts:
        return None

    if not _is_status_change_event(contexts):
        return None

    new_status = _first_status_value(contexts)
    if _normalize_text(new_status) != RESEARCH_STATUS:
        return None

    issue_id = _first_string(contexts, ISSUE_ID_KEYS)
    title = _first_string(contexts, ("title", "name"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _candidate_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)

    add(event)
    for key in ("automation_trigger_info", "automationTriggerInfo"):
        wrapper = event.get(key)
        add(wrapper)
        if isinstance(wrapper, Mapping):
            add(wrapper.get("triggerContext"))
            add(wrapper.get("trigger_context"))

    add(event.get("triggerContext"))
    add(event.get("trigger_context"))

    data = event.get("data")
    add(data)
    if isinstance(data, Mapping):
        add(data.get("issue"))
        add(data.get("state"))
        add(data.get("workflowState"))

    issue = event.get("issue")
    add(issue)
    if isinstance(issue, Mapping):
        add(issue.get("state"))
        add(issue.get("workflowState"))

    return contexts


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    trigger_values = _all_strings(
        contexts,
        (
            "trigger",
            "webhookType",
            "webhook_type",
            "action",
            "type",
            "event",
            "eventType",
            "event_type",
        ),
    )
    normalized_triggers = {_normalize_text(value) for value in trigger_values}

    if any(
        normalized in {
            "status changed",
            "status change",
            "state changed",
            "state change",
            "workflow state changed",
            "workflow state change",
        }
        for normalized in normalized_triggers
    ):
        return True

    updated_event = any(
        normalized in {"issue updated", "updated issue", "update", "updated"}
        for normalized in normalized_triggers
    )
    return updated_event and _updated_fields_include_status(contexts)


def _updated_fields_include_status(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "updated_fields"):
            if _values_include_status_field(context.get(key)):
                return True
        for key in ("changes", "changedFields", "changed_fields"):
            changes = context.get(key)
            if isinstance(changes, Mapping):
                if _values_include_status_field(changes.keys()):
                    return True
            elif _values_include_status_field(changes):
                return True
    return False


def _values_include_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_text(value) in STATUS_FIELD_NAMES
    if isinstance(value, Mapping):
        return _values_include_status_field(value.keys())
    if isinstance(value, Iterable):
        return any(_values_include_status_field(item) for item in value)
    return False


def _first_status_value(contexts: list[Mapping[str, Any]]) -> str | None:
    explicit = _first_string(contexts, EXPLICIT_NEW_STATUS_KEYS)
    if explicit:
        return explicit

    for context in contexts:
        changes = context.get("changes")
        if isinstance(changes, Mapping):
            for field_name in ("status", "state", "workflowState", "workflow_state"):
                change = changes.get(field_name)
                status = _status_from_change(change)
                if status:
                    return status

    for context in contexts:
        for key in STATUS_FALLBACK_KEYS:
            status = _string_or_name(context.get(key))
            if status:
                return status

    return None


def _status_from_change(change: Any) -> str | None:
    if isinstance(change, Mapping):
        for key in ("newValue", "new_value", "to", "after", "name"):
            status = _string_or_name(change.get(key))
            if status:
                return status
    return _string_or_name(change)


def _first_string(contexts: list[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for context in contexts:
        for key in keys:
            value = _string_or_name(context.get(key))
            if value:
                return value
    return None


def _all_strings(contexts: list[Mapping[str, Any]], keys: Iterable[str]) -> list[str]:
    values: list[str] = []
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                values.append(value)
    return values


def _string_or_name(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            nested = _string_or_name(value.get(key))
            if nested:
                return nested
    return None


def _has_research_prefix(title: str) -> bool:
    return title.strip().lower().startswith(TITLE_PREFIX.lower())


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""
    with_spaces = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    normalized = re.sub(r"[^A-Za-z0-9]+", " ", with_spaces)
    return re.sub(r"\s+", " ", normalized).strip().lower()


def main() -> int:
    """Read a JSON event from stdin and print the computed action as JSON."""
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(json.dumps({"error": f"invalid JSON: {exc.msg}"}), file=sys.stderr)
        return 1

    action = build_issue_title_update(event)
    print(json.dumps(action, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
