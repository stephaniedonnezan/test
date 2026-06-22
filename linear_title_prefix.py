"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflow state",
    "workflowstate",
    "status id",
    "state id",
    "workflow state id",
    "workflowstate id",
}
GENERIC_UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}
DIRECT_STATUS_TRIGGERS = {
    "status changed",
    "status change",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
}
PREFIX_RE = re.compile(r"^\s*cursor researching\b", re.IGNORECASE)


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue-title update action when a Linear issue moves to research.

    The automation payload may be Cursor's flat ``triggerContext`` shape or a
    nested Linear webhook payload. This function only describes the desired
    update; the caller is responsible for applying it to Linear.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_research_status_change(contexts):
        return None

    issue_id = _issue_id(contexts)
    title = _title(contexts)
    if not issue_id or not title:
        return None

    clean_title = title.strip()
    if PREFIX_RE.match(clean_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {clean_title}",
    }


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        contexts.append(trigger_context)
        _append_nested_issue_contexts(contexts, trigger_context)

    automation_info = event.get("automation_trigger_info")
    if isinstance(automation_info, Mapping):
        trigger_context = automation_info.get("triggerContext")
        if isinstance(trigger_context, Mapping):
            contexts.append(trigger_context)
            _append_nested_issue_contexts(contexts, trigger_context)

    _append_nested_issue_contexts(contexts, event)

    data = event.get("data")
    if isinstance(data, Mapping):
        contexts.append(data)

    contexts.append(event)
    return contexts


def _append_nested_issue_contexts(
    contexts: list[Mapping[str, Any]], source: Mapping[str, Any]
) -> None:
    for key in ("issue", "data"):
        value = source.get(key)
        if isinstance(value, Mapping):
            issue = value.get("issue") if key == "data" else value
            if isinstance(issue, Mapping):
                contexts.append(issue)


def _is_research_status_change(contexts: Sequence[Mapping[str, Any]]) -> bool:
    trigger_names = {
        normalized
        for context in contexts
        for key in ("trigger", "action", "type", "webhookType")
        if (normalized := _normalize_words(context.get(key)))
    }

    is_status_change = bool(trigger_names & DIRECT_STATUS_TRIGGERS)
    is_generic_update = bool(trigger_names & GENERIC_UPDATE_TRIGGERS)
    if not is_status_change and not (is_generic_update and _has_status_change(contexts)):
        return False

    return _normalize_words(_changed_status(contexts)) == TARGET_STATUS


def _has_status_change(contexts: Sequence[Mapping[str, Any]]) -> bool:
    if _first_value(contexts, ("newStatus", "new_status", "newState", "new_state")):
        return True

    for context in contexts:
        for key in ("updatedFields", "changedFields", "updatedProperties"):
            if _contains_status_field(context.get(key)):
                return True

        for key in ("changes", "updatedFrom", "updated_from"):
            changes = context.get(key)
            if isinstance(changes, Mapping):
                if any(_is_status_field(field) for field in changes):
                    return True
            elif isinstance(changes, Sequence) and not isinstance(changes, (str, bytes)):
                for change in changes:
                    if isinstance(change, Mapping) and _is_status_field(change.get("field")):
                        return True
                    if _is_status_field(change):
                        return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(_is_status_field(field) for field in value)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return any(
            _is_status_field(item.get("field") if isinstance(item, Mapping) else item)
            for item in value
        )
    return _is_status_field(value)


def _changed_status(contexts: Sequence[Mapping[str, Any]]) -> Any:
    for context in contexts:
        status = _status_from_changes(context.get("changes"))
        if status:
            return status

    explicit_status = _first_value(
        contexts,
        (
            "newStatus",
            "new_status",
            "newState",
            "new_state",
            "newWorkflowState",
            "new_workflow_state",
            "statusName",
            "stateName",
            "workflowStateName",
        ),
    )
    if explicit_status:
        return explicit_status

    for key in ("status", "state", "workflowState", "workflow_state"):
        value = _first_value(contexts, (key,))
        status = _status_name(value)
        if status:
            return status

    return None


def _status_from_changes(changes: Any) -> Any:
    if isinstance(changes, Mapping):
        for field, value in changes.items():
            if _is_status_field(field):
                return _status_name_from_change(value)
    elif isinstance(changes, Sequence) and not isinstance(changes, (str, bytes)):
        for change in changes:
            if not isinstance(change, Mapping):
                continue
            if _is_status_field(change.get("field")):
                return _status_name_from_change(change)
    return None


def _status_name_from_change(value: Any) -> Any:
    if isinstance(value, Mapping):
        for key in ("newValue", "new", "to", "after", "current", "name"):
            if key in value:
                return _status_name(value[key])
    return _status_name(value)


def _status_name(value: Any) -> Any:
    if isinstance(value, Mapping):
        for key in ("name", "label", "title"):
            if key in value:
                return value[key]
    return value


def _issue_id(contexts: Sequence[Mapping[str, Any]]) -> str | None:
    value = _first_value(contexts, ("issueId", "issue_id", "identifier", "key", "id"))
    return _clean_string(value)


def _title(contexts: Sequence[Mapping[str, Any]]) -> str | None:
    return _clean_string(_first_value(contexts, ("title", "name")))


def _first_value(contexts: Sequence[Mapping[str, Any]], keys: Sequence[str]) -> Any:
    for key in keys:
        for context in contexts:
            if key in context and context[key] not in (None, ""):
                return context[key]
    return None


def _is_status_field(value: Any) -> bool:
    return _normalize_words(value) in STATUS_FIELD_NAMES


def _normalize_words(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    camel_spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    normalized = re.sub(r"[^a-zA-Z0-9]+", " ", camel_spaced).strip().lower()
    return re.sub(r"\s+", " ", normalized)


def _clean_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    print(json.dumps(action, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
