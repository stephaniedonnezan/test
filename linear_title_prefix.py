"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_TRIGGER_KEYS = ("trigger", "action", "type", "event", "webhookType", "webhook_type")
_DIRECT_STATUS_CHANGE_EVENTS = {
    "status changed",
    "status change",
    "status updated",
    "state changed",
    "state change",
    "workflow state changed",
    "issue status changed",
}
_GENERIC_UPDATE_EVENTS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}
_STATUS_FIELD_NAMES = {"status", "state", "workflow state"}
_EXPLICIT_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "toStatus",
    "to_status",
    "statusName",
    "status_name",
    "stateName",
    "state_name",
    "workflowStateName",
    "workflow_state_name",
)
_ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "key", "id")
_TITLE_KEYS = ("title", "name", "summary")


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update action for Linear issues moved to "to research".

    The automation payloads used by Cursor and Linear vary slightly between flat
    trigger contexts and nested webhook shapes. This function accepts both and
    returns a small declarative action for the caller to execute.
    """

    if not isinstance(event, Mapping):
        return None

    candidates = _candidate_mappings(event)
    if not _is_status_change_event(candidates):
        return None

    new_status = _extract_new_status(candidates)
    if _normalize_label(new_status) != TARGET_STATUS:
        return None

    issue_id = _first_string(candidates, _ISSUE_ID_KEYS)
    title = _first_string(candidates, _TITLE_KEYS)
    if not issue_id or not title:
        return None

    stripped_title = title.strip()
    if _has_research_prefix(stripped_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {stripped_title}",
    }


def _candidate_mappings(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    candidates: list[Mapping[str, Any]] = []

    for path in (
        ("automation_trigger_info", "triggerContext"),
        ("automationTriggerInfo", "triggerContext"),
        ("triggerContext",),
        ("trigger_context",),
    ):
        context = _mapping_at(event, path)
        if context is not None:
            _append_issue_related_mappings(candidates, context)

    _append_issue_related_mappings(candidates, event)
    return _dedupe_mappings(candidates)


def _append_issue_related_mappings(
    candidates: list[Mapping[str, Any]], mapping: Mapping[str, Any]
) -> None:
    for path in (("data", "issue"), ("issue",), ("data",)):
        nested = _mapping_at(mapping, path)
        if nested is not None:
            candidates.append(nested)
    candidates.append(mapping)


def _mapping_at(mapping: Mapping[str, Any], path: Iterable[str]) -> Mapping[str, Any] | None:
    current: Any = mapping
    for key in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current if isinstance(current, Mapping) else None


def _dedupe_mappings(mappings: Iterable[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    seen: set[int] = set()
    unique: list[Mapping[str, Any]] = []
    for mapping in mappings:
        identity = id(mapping)
        if identity not in seen:
            seen.add(identity)
            unique.append(mapping)
    return unique


def _is_status_change_event(candidates: Iterable[Mapping[str, Any]]) -> bool:
    normalized_triggers: list[str] = []
    status_field_changed = False

    for mapping in candidates:
        for key in _TRIGGER_KEYS:
            normalized = _normalize_label(mapping.get(key))
            if normalized:
                normalized_triggers.append(normalized)
        if _mapping_has_status_change_metadata(mapping):
            status_field_changed = True

    if any(trigger in _DIRECT_STATUS_CHANGE_EVENTS for trigger in normalized_triggers):
        return True

    if status_field_changed and any(
        trigger in _GENERIC_UPDATE_EVENTS for trigger in normalized_triggers
    ):
        return True

    return False


def _mapping_has_status_change_metadata(mapping: Mapping[str, Any]) -> bool:
    updated_fields = mapping.get("updatedFields") or mapping.get("updated_fields")
    if _contains_status_field(updated_fields):
        return True

    for key in ("changes", "changedFields", "changed_fields"):
        changes = mapping.get(key)
        if isinstance(changes, Mapping) and any(
            _is_status_field_name(field) for field in changes.keys()
        ):
            return True
        if _contains_status_field(changes):
            return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field_name(value)
    if isinstance(value, Mapping):
        return any(_is_status_field_name(key) for key in value.keys())
    if isinstance(value, Iterable):
        return any(_contains_status_field(item) for item in value)
    return False


def _is_status_field_name(value: Any) -> bool:
    return _normalize_label(value) in _STATUS_FIELD_NAMES


def _extract_new_status(candidates: Iterable[Mapping[str, Any]]) -> str | None:
    candidate_list = list(candidates)

    for mapping in candidate_list:
        explicit = _first_string([mapping], _EXPLICIT_STATUS_KEYS)
        if explicit:
            return explicit

    for mapping in candidate_list:
        changed_status = _status_from_change_metadata(mapping)
        if changed_status:
            return changed_status

    for mapping in candidate_list:
        nested_status = _status_from_nested_status_object(mapping)
        if nested_status:
            return nested_status

    return _first_string(candidate_list, ("status", "state", "workflowState", "workflow_state"))


def _status_from_change_metadata(mapping: Mapping[str, Any]) -> str | None:
    for key in ("changes", "changedFields", "changed_fields"):
        changes = mapping.get(key)
        if not isinstance(changes, Mapping):
            continue

        for field, change in changes.items():
            if _is_status_field_name(field):
                status = _status_from_change_value(change)
                if status:
                    return status

    return None


def _status_from_change_value(value: Any) -> str | None:
    if isinstance(value, str):
        return value

    if isinstance(value, Mapping):
        for key in ("to", "after", "new", "newValue", "new_value", "current"):
            status = _status_from_change_value(value.get(key))
            if status:
                return status
        return _status_from_nested_status_object(value)

    return None


def _status_from_nested_status_object(mapping: Mapping[str, Any]) -> str | None:
    for key in ("status", "state", "workflowState", "workflow_state"):
        value = mapping.get(key)
        if isinstance(value, str):
            return value
        if isinstance(value, Mapping):
            status_name = _first_string([value], ("name", "title", "status"))
            if status_name:
                return status_name
    return None


def _first_string(
    mappings: Iterable[Mapping[str, Any]], keys: Iterable[str]
) -> str | None:
    for mapping in mappings:
        for key in keys:
            value = mapping.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def _normalize_label(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value.strip())
    normalized = re.sub(r"[^a-zA-Z0-9]+", " ", spaced).strip().lower()
    return re.sub(r"\s+", " ", normalized)


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    result = build_issue_title_update(event)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
