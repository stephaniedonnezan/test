"""Build Linear issue title updates for research-status automations."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"

_STATUS_CHANGE_VALUES = {
    "statuschanged",
    "statechanged",
    "workflowstatechanged",
}
_UPDATE_VALUES = {
    "issueupdated",
    "updatedissue",
    "update",
}
_EVENT_FIELD_NAMES = ("trigger", "action", "type", "webhookType", "webhook_type")
_NEW_STATUS_FIELD_NAMES = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "newWorkflowState",
    "new_workflow_state",
    "statusName",
    "status_name",
    "stateName",
    "state_name",
    "workflowStateName",
    "workflow_state_name",
)
_UPDATED_FIELD_NAMES = (
    "updatedFields",
    "updated_fields",
    "changedFields",
    "changed_fields",
    "changes",
    "updatedFrom",
    "updated_from",
)
_STATUS_FIELD_VALUES = {
    "status",
    "statusid",
    "state",
    "stateid",
    "workflowstate",
    "workflowstateid",
}
_PREFIX_RE = re.compile(r"^\s*cursor\s+researching\b", re.IGNORECASE)


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to to research.

    The function is intentionally side-effect free so the surrounding automation
    can decide how to apply the returned update.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = list(_candidate_contexts(event))
    if not _is_status_change_event(contexts):
        return None

    new_status = _extract_new_status(contexts)
    if _normalize_text(new_status) != TARGET_STATUS:
        return None

    issue_id = _extract_issue_id(contexts)
    title = _extract_issue_title(contexts)
    if not issue_id or not title or _has_prefix(title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id,
        "title": f"{PREFIX}: {title.strip()}",
    }


def _candidate_contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely issue payload contexts, most specific first."""

    seen: set[int] = set()

    def yield_once(value: Any) -> Iterable[Mapping[str, Any]]:
        if isinstance(value, Mapping) and id(value) not in seen:
            seen.add(id(value))
            yield value

    trigger_context = event.get("triggerContext")
    data = event.get("data")
    issue = event.get("issue")
    trigger_data = trigger_context.get("data") if isinstance(trigger_context, Mapping) else None
    trigger_issue = trigger_context.get("issue") if isinstance(trigger_context, Mapping) else None

    if isinstance(data, Mapping):
        yield from yield_once(data.get("issue"))
    yield from yield_once(issue)
    yield from yield_once(data)
    if isinstance(trigger_data, Mapping):
        yield from yield_once(trigger_data.get("issue"))
    yield from yield_once(trigger_issue)
    yield from yield_once(trigger_data)
    yield from yield_once(trigger_context)
    yield from yield_once(event)


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    event_values = [
        value
        for context in contexts
        for name in _EVENT_FIELD_NAMES
        if (value := context.get(name)) is not None
    ]

    if any(_compact_text(value) in _STATUS_CHANGE_VALUES for value in event_values):
        return True

    if not any(_compact_text(value) in _UPDATE_VALUES for value in event_values):
        return False

    return _updated_fields_include_status(contexts)


def _updated_fields_include_status(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for name in _UPDATED_FIELD_NAMES:
            value = context.get(name)
            if value is None:
                continue
            if _value_mentions_status_field(value):
                return True
    return False


def _value_mentions_status_field(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(
            _compact_text(key) in _STATUS_FIELD_VALUES
            or _value_mentions_status_field(nested_value)
            for key, nested_value in value.items()
        )

    if isinstance(value, str):
        return _compact_text(value) in _STATUS_FIELD_VALUES

    if isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray)):
        return any(_value_mentions_status_field(item) for item in value)

    return False


def _extract_new_status(contexts: list[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        for name in _NEW_STATUS_FIELD_NAMES:
            value = context.get(name)
            if _string_or_nested_name(value):
                return _string_or_nested_name(value)

    for context in contexts:
        for name in ("status", "state", "workflowState", "workflow_state"):
            value = context.get(name)
            if _string_or_nested_name(value):
                return _string_or_nested_name(value)

    return None


def _string_or_nested_name(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None

    if isinstance(value, Mapping):
        for name in ("name", "title", "label"):
            nested_value = value.get(name)
            if isinstance(nested_value, str) and nested_value.strip():
                return nested_value.strip()

    return None


def _extract_issue_id(contexts: list[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        for name in ("id", "issueId", "issue_id", "identifier"):
            value = context.get(name)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _extract_issue_title(contexts: list[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        value = context.get("title")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _has_prefix(title: str) -> bool:
    return bool(_PREFIX_RE.match(title))


def _normalize_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    spaced_camel = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    normalized = re.sub(r"[^a-z0-9]+", " ", spaced_camel.lower()).strip()
    return re.sub(r"\s+", " ", normalized)


def _compact_text(value: Any) -> str:
    normalized = _normalize_text(value)
    return "" if normalized is None else normalized.replace(" ", "")


def main() -> int:
    event = json.load(sys.stdin)
    result = build_issue_title_update(event)
    if result is not None:
        json.dump(result, sys.stdout, sort_keys=True)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
