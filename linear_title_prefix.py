"""Build title-update actions for Linear issues moved to To Research.

The automation payloads used by Cursor and Linear are not identical, so this
module accepts both the flat ``triggerContext`` shape and nested Linear webhook
shapes.  The public helper returns a small action dict that an outer automation
runner can turn into the actual Linear API update.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


RESEARCH_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_DIRECT_STATUS_EVENTS = {
    "status changed",
    "status change",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
}

_ISSUE_UPDATE_EVENTS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}

_STATUS_FIELD_NAMES = {
    "status",
    "status id",
    "state",
    "state id",
    "workflow state",
    "workflow state id",
}

_EXPLICIT_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "newWorkflowState",
    "new_workflow_state",
    "toStatus",
    "to_status",
    "toState",
    "to_state",
    "toWorkflowState",
    "to_workflow_state",
    "statusName",
    "status_name",
    "stateName",
    "state_name",
    "workflowStateName",
    "workflow_state_name",
)

_CURRENT_STATUS_KEYS = (
    "status",
    "state",
    "workflowState",
    "workflow_state",
)

_TITLE_KEYS = (
    "title",
    "issueTitle",
    "issue_title",
)

_ISSUE_ID_KEYS = (
    "issueId",
    "issue_id",
    "id",
    "identifier",
    "key",
)


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear issue-title update action for To Research transitions.

    The function is intentionally side-effect free.  It returns ``None`` when
    the event is unrelated, incomplete, or the issue title is already prefixed.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    status = _extract_status(event)
    if _normalize(status) != TARGET_STATUS:
        return None

    issue_id = _extract_first_text(event, _ISSUE_ID_KEYS)
    title = _extract_first_text(event, _TITLE_KEYS)
    if not issue_id or not title:
        return None

    title = title.strip()
    if re.match(rf"^\s*{re.escape(RESEARCH_PREFIX)}\b", title, re.IGNORECASE):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{RESEARCH_PREFIX}: {title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    event_names = {
        normalized
        for value in _iter_event_name_values(event)
        if (normalized := _normalize(value))
    }

    if event_names.intersection(_DIRECT_STATUS_EVENTS):
        return True

    if event_names.intersection(_ISSUE_UPDATE_EVENTS):
        return _has_status_changed_marker(event)

    return False


def _iter_event_name_values(value: Any) -> Iterable[Any]:
    for mapping in _walk_mappings(value):
        for key in (
            "trigger",
            "action",
            "type",
            "webhookType",
            "webhook_type",
            "event",
            "eventType",
            "event_type",
        ):
            if key in mapping:
                yield mapping[key]


def _has_status_changed_marker(event: Mapping[str, Any]) -> bool:
    for mapping in _walk_mappings(event):
        for key in (
            "updatedFields",
            "updated_fields",
            "changedFields",
            "changed_fields",
            "fields",
        ):
            if key in mapping and _contains_status_field_name(mapping[key]):
                return True

        for key in ("changes", "changed", "updatedFrom", "updated_from"):
            if key in mapping and _contains_status_field_name(mapping[key]):
                return True

    return False


def _contains_status_field_name(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(
            _normalize(key) in _STATUS_FIELD_NAMES
            or _contains_status_field_name(child)
            for key, child in value.items()
        )

    if isinstance(value, list | tuple | set):
        return any(_contains_status_field_name(item) for item in value)

    return _normalize(value) in _STATUS_FIELD_NAMES


def _extract_status(event: Mapping[str, Any]) -> str | None:
    for mapping in _priority_mappings(event):
        for key in _EXPLICIT_STATUS_KEYS:
            if key in mapping and (status := _string_value(mapping[key])):
                return status

        for key in ("changes", "changed", "statusChange", "stateChange"):
            if key in mapping and (status := _status_from_change(mapping[key])):
                return status

    for mapping in _priority_mappings(event):
        for key in _CURRENT_STATUS_KEYS:
            if key in mapping and (status := _string_value(mapping[key])):
                return status

    return None


def _status_from_change(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("new", "to", "after", "current", "value", "name"):
            if key in value and (status := _string_value(value[key])):
                return status

        for key, child in value.items():
            if _normalize(key) in _STATUS_FIELD_NAMES:
                if status := _status_from_change(child):
                    return status
                if status := _string_value(child):
                    return status

        for child in value.values():
            if status := _status_from_change(child):
                return status

    if isinstance(value, list | tuple):
        for item in value:
            if status := _status_from_change(item):
                return status

    return None


def _extract_first_text(event: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for mapping in _priority_mappings(event):
        for key in keys:
            if key in mapping and (value := _string_value(mapping[key])):
                return value
    return None


def _priority_mappings(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    mappings: list[Mapping[str, Any]] = []

    for key in ("triggerContext", "trigger_context"):
        if isinstance(event.get(key), Mapping):
            mappings.append(event[key])

    data = event.get("data")
    if isinstance(data, Mapping):
        for key in ("issue", "node"):
            if isinstance(data.get(key), Mapping):
                mappings.append(data[key])
        mappings.append(data)

    for key in ("issue", "node", "payload"):
        if isinstance(event.get(key), Mapping):
            mappings.append(event[key])

    mappings.append(event)

    seen: set[int] = set()
    unique_mappings: list[Mapping[str, Any]] = []
    for mapping in mappings:
        identifier = id(mapping)
        if identifier not in seen:
            seen.add(identifier)
            unique_mappings.append(mapping)
    return unique_mappings


def _walk_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for child in value.values():
            yield from _walk_mappings(child)
    elif isinstance(value, list | tuple):
        for child in value:
            yield from _walk_mappings(child)


def _string_value(value: Any) -> str | None:
    if value is None:
        return None

    if isinstance(value, Mapping):
        for key in ("name", "title", "label", "displayName", "display_name"):
            if key in value and (text := _string_value(value[key])):
                return text
        return None

    text = str(value).strip()
    return text or None


def _normalize(value: Any) -> str | None:
    text = _string_value(value)
    if text is None:
        return None

    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def main() -> int:
    """Read a JSON event from stdin and print the computed action, if any."""

    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 2

    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
