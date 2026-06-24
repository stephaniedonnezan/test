"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any, Iterable


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {"status", "state", "workflow state", "workflowstate"}
_DIRECT_STATUS_CHANGE_TRIGGERS = {
    "status changed",
    "status change",
    "status updated",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
}
_UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return the Linear title update action for issues entering research.

    The function is intentionally side-effect free. Automation callers can pass
    flat Cursor trigger contexts, wrapped Cloud automation payloads, or nested
    Linear webhook payloads and apply the returned action through their Linear
    client.
    """

    if not isinstance(event, Mapping):
        return None

    envelopes = _automation_envelopes(event)
    context = _first_mapping(*envelopes, keys=("triggerContext", "trigger_context"))
    data = _first_mapping(*envelopes, keys=("data", "payload"))
    issue = _extract_issue(event, context, data)

    if _normalize_text(_extract_new_status(event, context, data, issue)) != TARGET_STATUS:
        return None

    if not _is_status_change_event(event, context, data):
        return None

    issue_id = _extract_first_string(
        issue,
        context,
        event,
        keys=("identifier", "key", "issueId", "issue_id", "id"),
    )
    title = _extract_first_string(issue, context, event, keys=("title", "name"))
    if not issue_id or not title or _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _automation_envelopes(event: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    envelopes: list[Mapping[str, Any]] = [event]
    for key in (
        "automation_trigger_info",
        "automationTriggerInfo",
        "triggerInfo",
        "trigger_info",
    ):
        value = event.get(key)
        if isinstance(value, Mapping):
            envelopes.append(value)
    return tuple(envelopes)


def _extract_issue(
    event: Mapping[str, Any],
    context: Mapping[str, Any],
    data: Mapping[str, Any],
) -> Mapping[str, Any]:
    candidates = (
        _first_mapping(data, keys=("issue",)),
        _first_mapping(event, keys=("issue",)),
        context,
        data,
        event,
    )
    for candidate in candidates:
        if _extract_first_string(candidate, keys=("title", "name")):
            return candidate
    for candidate in candidates:
        if _extract_first_string(
            candidate,
            keys=("identifier", "key", "issueId", "issue_id", "id"),
        ):
            return candidate
    return {}


def _extract_new_status(*sources: Mapping[str, Any]) -> str | None:
    explicit_keys = (
        "newStatus",
        "new_status",
        "toStatus",
        "to_status",
        "statusTo",
        "status_to",
        "newState",
        "new_state",
        "toState",
        "to_state",
        "newWorkflowState",
        "new_workflow_state",
    )
    fallback_keys = ("status", "state", "workflowState", "workflow_state")

    for source in sources:
        value = _extract_first_string(source, keys=explicit_keys)
        if value:
            return value

    for source in sources:
        value = _extract_status_from_changes(source)
        if value:
            return value

    for source in sources:
        value = _extract_first_string(source, keys=fallback_keys)
        if value:
            return value

    return None


def _extract_status_from_changes(source: Mapping[str, Any]) -> str | None:
    for key in ("changes", "changed", "updatedFields", "updated_fields"):
        value = source.get(key)
        if isinstance(value, Mapping):
            status = _extract_status_from_mapping(value)
            if status:
                return status
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, Mapping):
                    status = _extract_status_from_mapping(item)
                    if status:
                        return status
    return None


def _extract_status_from_mapping(source: Mapping[str, Any]) -> str | None:
    for key, value in source.items():
        normalized_key = _normalize_text(str(key))
        if normalized_key in _STATUS_FIELD_NAMES:
            return _string_from_status_value(value)

        if isinstance(value, Mapping):
            field_name = _extract_first_string(value, keys=("field", "fieldName", "name"))
            if _normalize_text(field_name) in _STATUS_FIELD_NAMES:
                status = _extract_first_string(
                    value,
                    keys=("to", "new", "newValue", "after", "value", "name"),
                )
                if status:
                    return status
    return None


def _string_from_status_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        return _extract_first_string(
            value,
            keys=("to", "new", "newValue", "after", "value", "name"),
        )
    return _coerce_string(value)


def _is_status_change_event(*sources: Mapping[str, Any]) -> bool:
    trigger_values = {
        _normalize_text(value)
        for source in sources
        for value in _iter_trigger_values(source)
    }
    if trigger_values & _DIRECT_STATUS_CHANGE_TRIGGERS:
        return True

    if trigger_values & _UPDATE_TRIGGERS:
        return any(_updated_fields_include_status(source) for source in sources)

    return False


def _iter_trigger_values(source: Mapping[str, Any]) -> Iterable[str]:
    trigger_keys = {
        "trigger",
        "triggerType",
        "trigger_type",
        "webhookType",
        "webhook_type",
        "action",
        "type",
        "event",
        "eventType",
        "event_type",
    }
    for key, value in source.items():
        if key in trigger_keys:
            text = _coerce_string(value)
            if text:
                yield text
        elif isinstance(value, Mapping):
            yield from _iter_trigger_values(value)


def _updated_fields_include_status(source: Mapping[str, Any]) -> bool:
    for key in (
        "updatedFields",
        "updated_fields",
        "changedFields",
        "changed_fields",
        "changes",
        "changed",
        "updatedFrom",
        "updated_from",
    ):
        value = source.get(key)
        if _value_mentions_status_field(value):
            return True
    return False


def _value_mentions_status_field(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, nested_value in value.items():
            if _normalize_text(str(key)) in _STATUS_FIELD_NAMES:
                return True
            if _value_mentions_status_field(nested_value):
                return True
        return False

    if isinstance(value, list):
        return any(_value_mentions_status_field(item) for item in value)

    return _normalize_text(_coerce_string(value)) in _STATUS_FIELD_NAMES


def _first_mapping(
    *sources: Mapping[str, Any],
    keys: tuple[str, ...],
) -> Mapping[str, Any]:
    for source in sources:
        for key in keys:
            value = source.get(key)
            if isinstance(value, Mapping):
                return value
    return {}


def _extract_first_string(
    *sources: Mapping[str, Any],
    keys: tuple[str, ...],
) -> str | None:
    for source in sources:
        for key in keys:
            value = source.get(key)
            text = _string_from_status_value(value)
            if text:
                return text
    return None


def _coerce_string(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""

    with_spaces = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    normalized = re.sub(r"[^a-zA-Z0-9]+", " ", with_spaces).casefold()
    return " ".join(normalized.split())


def _has_research_prefix(title: str) -> bool:
    return title.strip().casefold().startswith(TITLE_PREFIX.casefold())


def main() -> int:
    payload = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(payload), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
