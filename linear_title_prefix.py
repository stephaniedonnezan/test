"""Build Linear issue-title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


RESEARCH_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_DIRECT_STATUS_CHANGE_EVENTS = {
    "status changed",
    "status change",
    "status updated",
    "state changed",
    "state change",
    "state updated",
    "workflow state changed",
    "workflow state change",
    "workflow state updated",
}
_GENERIC_UPDATE_EVENTS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}
_NEW_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "newWorkflowState",
    "new_workflow_state",
    "newWorkflowStateName",
    "new_workflow_state_name",
)
_STATUS_VALUE_KEYS = (
    *_NEW_STATUS_KEYS,
    "status",
    "statusName",
    "status_name",
    "state",
    "stateName",
    "state_name",
    "workflowState",
    "workflow_state",
    "workflowStateName",
    "workflow_state_name",
)
_EVENT_KEYS = ("trigger", "event", "action", "type", "webhookType", "webhook_type")
_STATUS_FIELD_NAMES = {
    "status",
    "status id",
    "state",
    "state id",
    "workflow state",
    "workflow state id",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return an issue-title update when a Linear issue moves to "to research".

    The automation runner can pass either a flat trigger context or a nested
    webhook payload. This function keeps the decision side-effect free so the
    caller can decide how to apply the returned update.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = tuple(_candidate_contexts(event))
    if not _event_indicates_status_change(contexts):
        return None

    status = _extract_status(contexts)
    if _normalize_text(status) != TARGET_STATUS:
        return None

    issue_id = _extract_first_string(contexts, ("issueId", "issue_id", "id", "identifier", "key"))
    title = _extract_first_string(contexts, ("title",))
    if not issue_id or not title:
        return None

    stripped_title = title.strip()
    if not stripped_title or _has_research_prefix(stripped_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{RESEARCH_PREFIX}: {stripped_title}",
    }


def _event_indicates_status_change(contexts: tuple[Mapping[str, Any], ...]) -> bool:
    saw_generic_update = False

    for context in contexts:
        for key in _EVENT_KEYS:
            event_name = _normalize_text(context.get(key))
            if event_name in _DIRECT_STATUS_CHANGE_EVENTS:
                return True
            if event_name in _GENERIC_UPDATE_EVENTS:
                saw_generic_update = True

    return saw_generic_update and _has_status_change_evidence(contexts)


def _has_status_change_evidence(contexts: tuple[Mapping[str, Any], ...]) -> bool:
    for context in contexts:
        if any(key in context for key in _NEW_STATUS_KEYS):
            return True

        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            if _contains_status_field(context.get(key)):
                return True

        for key in ("changes", "changed", "updatedFrom", "updated_from", "previousValues"):
            changed = context.get(key)
            if isinstance(changed, Mapping) and any(_is_status_field_name(field) for field in changed):
                return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field_name(value)
    if isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray, Mapping)):
        return any(_is_status_field_name(item) for item in value)
    return False


def _is_status_field_name(value: Any) -> bool:
    return _normalize_text(value) in _STATUS_FIELD_NAMES


def _extract_status(contexts: tuple[Mapping[str, Any], ...]) -> str | None:
    for key_group in (_NEW_STATUS_KEYS, _STATUS_VALUE_KEYS):
        for context in contexts:
            value = _extract_value(context, key_group)
            if value:
                return value
    return None


def _extract_first_string(
    contexts: tuple[Mapping[str, Any], ...],
    keys: tuple[str, ...],
) -> str | None:
    for context in contexts:
        value = _extract_value(context, keys)
        if value:
            return value
    return None


def _extract_value(context: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = context.get(key)
        if isinstance(value, Mapping):
            value = value.get("name") or value.get("title") or value.get("label")
        if isinstance(value, str) and value.strip():
            return value
    return None


def _candidate_contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    seen: set[int] = set()

    def add(context: Any) -> Iterable[Mapping[str, Any]]:
        if not isinstance(context, Mapping) or id(context) in seen:
            return
        seen.add(id(context))
        yield context

    yield from add(event)

    trigger_context = event.get("triggerContext")
    yield from add(trigger_context)

    issue = event.get("issue")
    yield from add(issue)

    data = event.get("data")
    yield from add(data)
    if isinstance(data, Mapping):
        yield from add(data.get("issue"))

    if isinstance(trigger_context, Mapping):
        yield from add(trigger_context.get("issue"))
        trigger_data = trigger_context.get("data")
        yield from add(trigger_data)
        if isinstance(trigger_data, Mapping):
            yield from add(trigger_data.get("issue"))


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(RESEARCH_PREFIX.casefold())


def _normalize_text(value: Any) -> str:
    if isinstance(value, Mapping):
        value = value.get("name") or value.get("title") or value.get("label")
    if not isinstance(value, str):
        return ""

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    normalized = re.sub(r"[^A-Za-z0-9]+", " ", spaced).strip().lower()
    return " ".join(normalized.split())


def _main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(build_issue_title_update(event), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
