"""Build Linear issue title updates for research-status automations.

The module intentionally returns an action payload instead of calling Linear
directly. That keeps the decision logic easy to test and lets the automation
runner own the side effect.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = frozenset({"status", "state", "workflowstate", "workflow_state"})


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title-update action when an issue moves to "to research".

    Supported payloads include the flat Cursor automation trigger context and
    nested Linear issue webhook shapes. Non-status changes, non-target statuses,
    missing issue data, and already-prefixed titles return ``None``.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    new_status = _extract_new_status(event)
    if _normalize_text(new_status) != _normalize_text(TARGET_STATUS):
        return None

    issue_id = _extract_issue_id(event)
    title = _extract_title(event)
    if not issue_id or not title:
        return None

    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    """Detect direct status-change triggers and Linear issue update payloads."""

    event_type_values = _event_type_values(event)
    if any(_normalize_text(value) == "status changed" for value in event_type_values):
        return True

    if not any(
        _normalize_text(value) in {"issue updated", "updated issue", "update", "issue"}
        for value in event_type_values
    ):
        return False

    return _mentions_status_field(event)


def _event_type_values(event: Mapping[str, Any]) -> list[Any]:
    values: list[Any] = []
    for mapping in _walk_mappings(event):
        for key in ("trigger", "action", "type", "webhookType", "webhook_type"):
            if key in mapping:
                values.append(mapping[key])
    return values


def _mentions_status_field(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, nested_value in value.items():
            normalized_key = _normalize_key(key)
            if normalized_key in {"updatedfields", "changedfields"}:
                if _field_collection_mentions_status(nested_value):
                    return True
            if normalized_key in {"changes", "changed", "updates"}:
                if _changes_mention_status(nested_value):
                    return True
            if _mentions_status_field(nested_value):
                return True
    elif isinstance(value, list):
        return any(_mentions_status_field(item) for item in value)

    return False


def _field_collection_mentions_status(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_key(value) in STATUS_FIELDS
    if isinstance(value, Mapping):
        return any(_normalize_key(key) in STATUS_FIELDS for key in value)
    if isinstance(value, list):
        return any(_field_collection_mentions_status(item) for item in value)
    return False


def _changes_mention_status(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, nested_value in value.items():
            if _normalize_key(key) in STATUS_FIELDS:
                return True
            if isinstance(nested_value, Mapping) and _normalize_key(
                nested_value.get("field") or nested_value.get("fieldName")
            ) in STATUS_FIELDS:
                return True
            if _changes_mention_status(nested_value):
                return True
    elif isinstance(value, list):
        return any(_changes_mention_status(item) for item in value)

    return False


def _extract_new_status(event: Mapping[str, Any]) -> str | None:
    status = _first_string(
        _values_for_keys(
            event,
            (
                "newStatus",
                "new_status",
                "statusName",
                "status_name",
                "newState",
                "new_state",
                "newWorkflowState",
                "new_workflow_state",
            ),
        )
    )
    if status:
        return status

    changed_status = _status_from_changes(event)
    if changed_status:
        return changed_status

    return _first_string(
        _values_for_keys(event, ("status", "state.name", "workflowState.name", "workflow_state.name"))
    )


def _status_from_changes(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key, nested_value in value.items():
            normalized_key = _normalize_key(key)
            if normalized_key in STATUS_FIELDS:
                status = _status_value_from_change(nested_value)
                if status:
                    return status
            if normalized_key in {"changes", "changed", "updates"}:
                status = _status_from_changes(nested_value)
                if status:
                    return status
            if isinstance(nested_value, Mapping) and _normalize_key(
                nested_value.get("field") or nested_value.get("fieldName")
            ) in STATUS_FIELDS:
                status = _status_value_from_change(nested_value)
                if status:
                    return status

            status = _status_from_changes(nested_value)
            if status:
                return status
    elif isinstance(value, list):
        for item in value:
            status = _status_from_changes(item)
            if status:
                return status

    return None


def _status_value_from_change(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, Mapping):
        return _first_string(
            (
                _read_path(value, path)
                for path in (
                    "to.name",
                    "new.name",
                    "after.name",
                    "to",
                    "newValue",
                    "new_value",
                    "after",
                    "value.name",
                    "value",
                    "name",
                )
            )
        )
    return None


def _extract_issue_id(event: Mapping[str, Any]) -> str | None:
    return _first_string(_values_for_keys(event, ("issueId", "issue_id", "identifier", "key", "id")))


def _extract_title(event: Mapping[str, Any]) -> str | None:
    issue_title = _first_string(
        _values_for_keys(event, ("issue.title", "data.issue.title", "triggerContext.title", "title"))
    )
    return issue_title


def _values_for_keys(event: Mapping[str, Any], keys: tuple[str, ...]) -> list[Any]:
    values: list[Any] = []
    for key in keys:
        direct_key = key if "." not in key else key.split(".")[-1]
        for mapping in _walk_mappings(event):
            if "." in key:
                value = _read_path(mapping, key)
                if value is not None:
                    values.append(value)
            if direct_key in mapping:
                values.append(mapping[direct_key])
    return values


def _walk_mappings(value: Any) -> list[Mapping[str, Any]]:
    mappings: list[Mapping[str, Any]] = []
    if isinstance(value, Mapping):
        mappings.append(value)
        for nested_value in value.values():
            mappings.extend(_walk_mappings(nested_value))
    elif isinstance(value, list):
        for item in value:
            mappings.extend(_walk_mappings(item))
    return mappings


def _read_path(mapping: Mapping[str, Any], path: str) -> Any:
    value: Any = mapping
    for part in path.split("."):
        if not isinstance(value, Mapping) or part not in value:
            return None
        value = value[part]
    return value


def _first_string(values: Any) -> str | None:
    for value in values:
        if isinstance(value, Mapping):
            value = value.get("name")
        if isinstance(value, str):
            stripped = value.strip()
            if stripped:
                return stripped
    return None


def _has_research_prefix(title: str) -> bool:
    return _normalize_text(title).startswith(_normalize_text(TITLE_PREFIX))


def _normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    words = re.sub(r"[^A-Za-z0-9]+", " ", spaced).strip().lower()
    return re.sub(r"\s+", " ", words)


def _normalize_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", _normalize_text(value))


def main() -> int:
    """Read a JSON event from stdin and print the title-update action, if any."""

    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 2

    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
