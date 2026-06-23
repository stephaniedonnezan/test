"""Build Linear issue title updates for research-status automations.

The Cursor automation runtime can pass either its compact triggerContext payload
or a nested Linear webhook payload. This module keeps the decision logic small
and side-effect free so the caller can apply the returned update action.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow state"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue-title update action when a Linear issue enters research.

    The returned dictionary is intentionally generic:
    {"action": "update_issue_title", "issueId": "...", "title": "..."}.
    Consumers can translate that into the Linear API call they use.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    if _normalize_status(_extract_new_status(event)) != TARGET_STATUS:
        return None

    issue_id = _extract_issue_id(event)
    current_title = _extract_title(event)
    if not issue_id or not current_title:
        return None

    stripped_title = current_title.strip()
    if _has_research_prefix(stripped_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {stripped_title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    trigger_values = _values_for_keys(
        event,
        ("trigger", "webhookType", "webhook_type", "action", "type", "eventType", "event_type"),
    )
    normalized_triggers = {_normalize_event_name(value) for value in trigger_values}

    if any(value in {"status changed", "status change", "statuschanged"} for value in normalized_triggers):
        return True

    if any(value in {"update", "updated", "issue update", "issue updated", "updated issue"} for value in normalized_triggers):
        return _updated_fields_include_status(event)

    return False


def _updated_fields_include_status(event: Mapping[str, Any]) -> bool:
    for value in _values_for_keys(event, ("updatedFields", "updated_fields")):
        if _field_collection_includes_status(value):
            return True

    for value in _values_for_keys(event, ("changes", "changedFields", "changed_fields")):
        if isinstance(value, Mapping):
            if any(_normalize_field_name(key) in STATUS_FIELD_NAMES for key in value.keys()):
                return True
        elif _field_collection_includes_status(value):
            return True

    return False


def _field_collection_includes_status(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_field_name(value) in STATUS_FIELD_NAMES

    if isinstance(value, Mapping):
        return any(_normalize_field_name(key) in STATUS_FIELD_NAMES for key in value.keys())

    if isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray)):
        return any(_normalize_field_name(item) in STATUS_FIELD_NAMES for item in value)

    return False


def _extract_new_status(event: Mapping[str, Any]) -> Any:
    explicit_status_keys = (
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
    for value in _values_for_keys(event, explicit_status_keys):
        status = _coerce_name(value)
        if status:
            return status

    for value in _values_for_keys(event, ("updatedFields", "updated_fields")):
        status = _status_from_updated_fields(value)
        if status:
            return status

    for value in _values_for_keys(event, ("changes", "changedFields", "changed_fields")):
        status = _status_from_changes(value)
        if status:
            return status

    for value in _values_for_keys(event, ("status", "state", "workflowState", "workflow_state")):
        status = _coerce_name(value)
        if status:
            return status

    return None


def _status_from_updated_fields(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key, field_value in value.items():
            if _normalize_field_name(key) in STATUS_FIELD_NAMES:
                status = _coerce_changed_value(field_value)
                if status:
                    return status
    return None


def _status_from_changes(value: Any) -> str | None:
    if not isinstance(value, Mapping):
        return None

    for key, change in value.items():
        if _normalize_field_name(key) not in STATUS_FIELD_NAMES:
            continue
        status = _coerce_changed_value(change)
        if status:
            return status

    return None


def _coerce_changed_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("to", "new", "after", "value", "name"):
            if key in value:
                status = _coerce_name(value[key])
                if status:
                    return status
    return _coerce_name(value)


def _extract_issue_id(event: Mapping[str, Any]) -> str | None:
    for key in ("issueId", "issue_id", "identifier", "key", "id"):
        for value in _values_for_keys(event, (key,)):
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _extract_title(event: Mapping[str, Any]) -> str | None:
    for value in _values_for_keys(event, ("title", "name")):
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _values_for_keys(event: Mapping[str, Any], keys: tuple[str, ...]) -> list[Any]:
    wanted = set(keys)
    values: list[Any] = []
    for mapping in _walk_mappings(event):
        for key, value in mapping.items():
            if key in wanted:
                values.append(value)
    return values


def _walk_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for child in value.values():
            yield from _walk_mappings(child)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_mappings(item)


def _coerce_name(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        for key in ("name", "title", "status", "state"):
            if key in value:
                name = _coerce_name(value[key])
                if name:
                    return name
    return None


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def _normalize_status(value: Any) -> str | None:
    name = _coerce_name(value)
    if name is None:
        return None
    return _normalize_words(name)


def _normalize_event_name(value: Any) -> str:
    name = _coerce_name(value)
    if not name:
        return ""
    return _normalize_words(name)


def _normalize_field_name(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return _normalize_words(value)


def _normalize_words(value: str) -> str:
    separated = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    separated = re.sub(r"[_\-]+", " ", separated)
    separated = re.sub(r"[^a-zA-Z0-9]+", " ", separated)
    return " ".join(separated.lower().split())


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as error:
        print(f"Invalid JSON: {error}", file=sys.stderr)
        return 1

    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
