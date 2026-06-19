"""Build Linear issue-title updates for research status changes.

The automation this module supports should add a "Cursor researching" marker
only when a Linear issue moves into the "to research" workflow state.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_CAMEL_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_PREFIX_PATTERN = re.compile(rf"^\s*{re.escape(PREFIX)}\b", re.IGNORECASE)
_STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow status", "workflow state"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action for Linear issues moved to "to research".

    The return value is intentionally transport-neutral so a caller can wire it
    to Linear MCP, GraphQL, or another issue-update adapter.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    new_status = _extract_new_status(event)
    if _normalize_status(new_status) != TARGET_STATUS:
        return None

    title = _extract_issue_title(event)
    issue_id = _extract_issue_id(event)
    if not title or not issue_id:
        return None

    title = title.strip()
    if not title or _has_cursor_researching_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    event_labels = [_normalize_label(value) for value in _event_label_values(event)]
    if any(_looks_like_status_change_label(label) for label in event_labels):
        return True

    looks_like_issue_update = any(_looks_like_issue_update_label(label) for label in event_labels)
    return looks_like_issue_update and _has_status_change_metadata(event)


def _event_label_values(value: Any) -> list[str]:
    labels: list[str] = []
    label_keys = {"trigger", "webhooktype", "action", "type", "eventtype"}

    def visit(candidate: Any) -> None:
        if isinstance(candidate, Mapping):
            for key, nested in candidate.items():
                normalized_key = _normalize_key(key)
                if normalized_key in label_keys and isinstance(nested, str):
                    labels.append(nested)
                elif normalized_key in {"triggercontext", "data", "issue", "webhook"}:
                    visit(nested)

    visit(value)
    return labels


def _looks_like_status_change_label(label: str) -> bool:
    words = set(label.split())
    return bool(words & {"status", "state", "workflow"}) and bool(words & {"change", "changed"})


def _looks_like_issue_update_label(label: str) -> bool:
    words = set(label.split())
    if "update" in words or "updated" in words:
        return True
    return "issue" in words and bool(words & {"change", "changed"})


def _has_status_change_metadata(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            normalized_key = _normalize_key(key)
            if normalized_key in {
                "newstatus",
                "newstate",
                "newworkflowstate",
                "statuschanged",
                "statechanged",
            }:
                return True
            if normalized_key in {"updatedfields", "changedfields"} and _contains_status_field(nested):
                return True
            if normalized_key in {"updatedfrom", "changes", "changed"} and _mentions_status_field(nested):
                return True
            if _has_status_change_metadata(nested):
                return True
    elif isinstance(value, list):
        return any(_has_status_change_metadata(item) for item in value)

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_field_name(value) in _STATUS_FIELD_NAMES
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes, Mapping)):
        return any(_contains_status_field(item) for item in value)
    return False


def _mentions_status_field(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(
            _normalize_field_name(key) in _STATUS_FIELD_NAMES or _mentions_status_field(nested)
            for key, nested in value.items()
        )
    if isinstance(value, list):
        return any(_mentions_status_field(item) for item in value)
    return _contains_status_field(value)


def _extract_new_status(event: Mapping[str, Any]) -> str | None:
    explicit_keys = (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "newWorkflowState",
        "new_workflow_state",
        "status",
        "state",
        "workflowState",
        "workflow_state",
    )
    return _first_string_from_issue_sources(event, explicit_keys)


def _extract_issue_title(event: Mapping[str, Any]) -> str | None:
    return _first_string_from_issue_sources(event, ("title", "issueTitle", "issue_title"))


def _extract_issue_id(event: Mapping[str, Any]) -> str | None:
    return _first_string_from_issue_sources(
        event,
        ("issueId", "issue_id", "id", "identifier", "key"),
    )


def _first_string_from_issue_sources(event: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    normalized_keys = tuple(_normalize_key(key) for key in keys)
    for source in _issue_sources(event):
        value = _first_string_for_keys(source, normalized_keys)
        if value is not None and value.strip():
            return value.strip()
    return None


def _issue_sources(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    sources: list[Mapping[str, Any]] = []

    def add(candidate: Any) -> None:
        if isinstance(candidate, Mapping):
            sources.append(candidate)

    trigger_context = event.get("triggerContext")
    add(trigger_context)
    if isinstance(trigger_context, Mapping):
        add(trigger_context.get("issue"))
        trigger_data = trigger_context.get("data")
        if isinstance(trigger_data, Mapping):
            add(trigger_data.get("issue"))
            add(trigger_data)

    add(event.get("issue"))
    data = event.get("data")
    if isinstance(data, Mapping):
        add(data.get("issue"))
        add(data)

    add(event)

    seen: set[int] = set()
    unique_sources: list[Mapping[str, Any]] = []
    for source in sources:
        source_id = id(source)
        if source_id not in seen:
            seen.add(source_id)
            unique_sources.append(source)
    return unique_sources


def _first_string_for_keys(value: Any, keys: tuple[str, ...]) -> str | None:
    if not isinstance(value, Mapping):
        return None

    normalized_items = [(_normalize_key(key), nested) for key, nested in value.items()]
    for wanted_key in keys:
        for normalized_key, nested in normalized_items:
            if normalized_key == wanted_key:
                string_value = _string_from_value(nested)
                if string_value is not None:
                    return string_value

    for nested in value.values():
        if isinstance(nested, Mapping):
            string_value = _first_string_for_keys(nested, keys)
            if string_value is not None:
                return string_value
        elif isinstance(nested, list):
            for item in nested:
                string_value = _first_string_for_keys(item, keys)
                if string_value is not None:
                    return string_value

    return None


def _string_from_value(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        for key in ("name", "title", "identifier", "key", "id"):
            nested = value.get(key)
            if isinstance(nested, str):
                return nested
    return None


def _has_cursor_researching_prefix(title: str) -> bool:
    return bool(_PREFIX_PATTERN.match(title))


def _normalize_status(value: str | None) -> str:
    return _normalize_label(value)


def _normalize_label(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    value = _CAMEL_BOUNDARY.sub(" ", value)
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _normalize_key(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _normalize_field_name(value: Any) -> str:
    return _normalize_label(value)


def main() -> int:
    """Read a JSON event from stdin and print the resulting update action."""

    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 2

    update = build_issue_title_update(event)
    print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
