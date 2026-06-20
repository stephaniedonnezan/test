"""Build Linear issue title updates for research-status transitions.

The automation runner passes webhook payloads from Linear/Cursor and applies
the returned action. This module stays intentionally small and dependency-free
so it can be exercised directly in tests and from stdin in smoke checks.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


RESEARCH_PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"

_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflow state",
    "workflow status",
}

_DIRECT_STATUS_CHANGE_EVENTS = {
    "status changed",
    "status change",
    "changed status",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow status changed",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue-title update action when an issue enters research.

    The returned shape is intentionally declarative; the surrounding automation
    can decide how to call Linear. Non-matching payloads return ``None``.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_transition_event(event):
        return None

    status = _extract_new_status(event)
    if _normalize(status) != RESEARCH_STATUS:
        return None

    issue_id = _extract_issue_id(event)
    title = _extract_title(event)
    if not issue_id or not title:
        return None

    clean_title = title.strip()
    if _has_research_prefix(clean_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{RESEARCH_PREFIX}: {clean_title}",
    }


def _is_status_transition_event(event: Mapping[str, Any]) -> bool:
    event_names = {
        _normalize(value)
        for payload in _walk_mappings(event)
        for key in ("trigger", "webhookType", "action", "type")
        for value in [_string_value(payload.get(key))]
        if value
    }

    if any(name in _DIRECT_STATUS_CHANGE_EVENTS for name in event_names):
        return True
    if any("status changed" in name or "state changed" in name for name in event_names):
        return True

    is_generic_update = any(
        name in {"update", "updated", "issue update", "issue updated", "updated issue"}
        or name.endswith(" updated")
        for name in event_names
    )
    return is_generic_update and _updated_fields_include_status(event)


def _updated_fields_include_status(event: Mapping[str, Any]) -> bool:
    for payload in _walk_mappings(event):
        for key in ("updatedFields", "changedFields", "updated_fields", "changed_fields"):
            if _fields_include_status(payload.get(key)):
                return True

        for key in ("changes", "changed", "updatedFrom", "updated_from"):
            changes = payload.get(key)
            if isinstance(changes, Mapping) and any(_is_status_field(field) for field in changes):
                return True

    return False


def _fields_include_status(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)

    if isinstance(value, Mapping):
        field_candidates = [
            value.get(key)
            for key in ("field", "name", "key", "property", "path")
            if value.get(key) is not None
        ]
        return any(_fields_include_status(candidate) for candidate in field_candidates) or any(
            _is_status_field(key) for key in value
        )

    if isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray, str)):
        return any(_fields_include_status(item) for item in value)

    return False


def _extract_new_status(event: Mapping[str, Any]) -> str | None:
    explicit_status_keys = (
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
        "stateTo",
        "state_to",
        "newWorkflowState",
        "new_workflow_state",
        "workflowStateTo",
        "workflow_state_to",
    )
    for payload in _candidate_payloads(event):
        value = _first_string_from_keys(payload, explicit_status_keys)
        if value:
            return value

    changed_value = _extract_status_from_changes(event)
    if changed_value:
        return changed_value

    for payload in _candidate_payloads(event):
        for key in ("status", "state", "workflowState", "workflow_status"):
            value = _string_value(payload.get(key))
            if value:
                return value

    return None


def _extract_status_from_changes(event: Mapping[str, Any]) -> str | None:
    target_value_keys = ("to", "new", "after", "current", "value", "name")
    for payload in _walk_mappings(event):
        for key in ("changes", "changed"):
            changes = payload.get(key)
            if not isinstance(changes, Mapping):
                continue

            for field, change in changes.items():
                if not _is_status_field(field):
                    continue

                if isinstance(change, Mapping):
                    value = _first_string_from_keys(change, target_value_keys)
                    if value:
                        return value
                else:
                    value = _string_value(change)
                    if value:
                        return value

    return None


def _extract_issue_id(event: Mapping[str, Any]) -> str | None:
    for payload in _candidate_payloads(event):
        value = _first_string_from_keys(payload, ("issueId", "issue_id", "identifier", "key", "id"))
        if value:
            return value
    return None


def _extract_title(event: Mapping[str, Any]) -> str | None:
    for payload in _candidate_payloads(event):
        value = _first_string_from_keys(payload, ("title",))
        if value and value.strip():
            return value
    return None


def _candidate_payloads(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return likely issue/context objects from most to least specific."""

    candidates: list[Mapping[str, Any]] = []

    automation_info = event.get("automation_trigger_info") or event.get("automationTriggerInfo")
    if isinstance(automation_info, Mapping):
        _append_mapping(candidates, automation_info.get("triggerContext"))
        _append_mapping(candidates, automation_info.get("trigger_context"))

    _append_mapping(candidates, event.get("triggerContext"))
    _append_mapping(candidates, event.get("trigger_context"))
    _append_mapping(candidates, event.get("issue"))

    data = event.get("data")
    if isinstance(data, Mapping):
        _append_mapping(candidates, data.get("issue"))
        _append_mapping(candidates, data)

    _append_mapping(candidates, event)
    return candidates


def _walk_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for nested in value.values():
            yield from _walk_mappings(nested)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_mappings(item)


def _append_mapping(candidates: list[Mapping[str, Any]], value: Any) -> None:
    if isinstance(value, Mapping) and value not in candidates:
        candidates.append(value)


def _first_string_from_keys(payload: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for key in keys:
        value = _string_value(payload.get(key))
        if value:
            return value
    return None


def _string_value(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None

    if isinstance(value, Mapping):
        return _first_string_from_keys(value, ("name", "title", "label", "value", "id"))

    return None


def _is_status_field(value: Any) -> bool:
    normalized = _normalize(_string_value(value))
    return normalized in _STATUS_FIELD_NAMES


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(RESEARCH_PREFIX.casefold())


def _normalize(value: str | None) -> str:
    if not value:
        return ""

    with_spaces = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    words_only = re.sub(r"[^A-Za-z0-9]+", " ", with_spaces)
    return " ".join(words_only.casefold().split())


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
