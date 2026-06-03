"""Build title updates for Linear issues entering research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"

_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflow state",
    "workflowstate",
}
_OLD_VALUE_KEYS = {
    "from",
    "old",
    "old status",
    "oldstatus",
    "previous",
    "previous status",
    "previousstatus",
    "updated from",
    "updatedfrom",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update action for issues moved to research.

    The Cursor automation trigger uses a flat ``triggerContext`` payload, while
    raw Linear webhooks commonly nest issue fields under ``data`` or ``issue``.
    This function accepts both shapes and returns a small action object that the
    caller can use to update the issue title.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    status = _extract_new_status(event)
    if _normalize(status) != TARGET_STATUS:
        return None

    title = _extract_issue_field(event, ("title",))
    if title is None:
        return None

    stripped_title = str(title).strip()
    if not stripped_title:
        return None
    if stripped_title.lower().startswith(TITLE_PREFIX.lower()):
        return None

    issue_id = _extract_issue_field(event, ("issueId", "issue_id", "identifier", "id"))
    if issue_id is None:
        return None

    stripped_issue_id = str(issue_id).strip()
    if not stripped_issue_id:
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": stripped_issue_id,
        "title": f"{TITLE_PREFIX}: {stripped_title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    trigger_values = _collect_values(
        event,
        ("trigger", "event", "eventType", "event_type", "type", "action"),
    )
    normalized_triggers = {_normalize(value) for value in trigger_values}

    if any(
        trigger in normalized_triggers
        for trigger in (
            "status changed",
            "status change",
            "state changed",
            "state change",
            "workflow state changed",
            "workflow state change",
            "issue status changed",
            "issue status change",
        )
    ):
        return True

    is_issue_update = bool(
        normalized_triggers
        & {
            "update",
            "updated",
            "issue updated",
            "updated issue",
        }
    )
    return is_issue_update and _updated_status_fields_present(event)


def _updated_status_fields_present(event: Mapping[str, Any]) -> bool:
    for mapping in _walk_mappings(event):
        for key, value in mapping.items():
            normalized_key = _normalize(key)
            if normalized_key in {"updated fields", "updatedfields", "changed fields", "changedfields"}:
                if _contains_status_field(value):
                    return True
            if normalized_key in {"updated from", "updatedfrom", "changes"}:
                if isinstance(value, Mapping) and any(_is_status_field_name(name) for name in value):
                    return True
    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field_name(value)
    if isinstance(value, Mapping):
        return any(_is_status_field_name(key) or _contains_status_field(item) for key, item in value.items())
    if isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray)):
        return any(_contains_status_field(item) for item in value)
    return False


def _is_status_field_name(value: Any) -> bool:
    normalized = _normalize(value)
    return normalized in _STATUS_FIELD_NAMES


def _extract_new_status(event: Mapping[str, Any]) -> str | None:
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
    for mapping in _walk_mappings(event, skip_old_values=True):
        for key in explicit_status_keys:
            if key in mapping:
                return _string_or_name(mapping[key])

    fallback_status_keys = ("status", "state", "workflowState", "workflow_state")
    for mapping in _walk_mappings(event, skip_old_values=True):
        for key in fallback_status_keys:
            if key in mapping:
                return _string_or_name(mapping[key])

    return None


def _string_or_name(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            if key in value and value[key] is not None:
                return str(value[key])
        return None
    return str(value)


def _extract_issue_field(event: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for mapping in _issue_contexts(event):
        for key in keys:
            value = mapping.get(key)
            if value is not None:
                return str(value)
    return None


def _issue_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)

    trigger_context = event.get("triggerContext")
    data = event.get("data")
    issue = event.get("issue")

    add(trigger_context)
    if isinstance(trigger_context, Mapping):
        add(trigger_context.get("issue"))
        add(trigger_context.get("data"))
        nested_data = trigger_context.get("data")
        if isinstance(nested_data, Mapping):
            add(nested_data.get("issue"))

    add(issue)
    add(data)
    if isinstance(data, Mapping):
        add(data.get("issue"))
    add(event)

    return contexts


def _collect_values(event: Mapping[str, Any], keys: tuple[str, ...]) -> list[Any]:
    values: list[Any] = []
    for mapping in _walk_mappings(event):
        for key in keys:
            if key in mapping and not isinstance(mapping[key], Mapping):
                values.append(mapping[key])
    return values


def _walk_mappings(value: Any, *, skip_old_values: bool = False) -> Iterable[Mapping[str, Any]]:
    if not isinstance(value, Mapping):
        return

    yield value
    for key, nested in value.items():
        if skip_old_values and _normalize(key) in _OLD_VALUE_KEYS:
            continue
        if isinstance(nested, Mapping):
            yield from _walk_mappings(nested, skip_old_values=skip_old_values)
        elif isinstance(nested, list):
            for item in nested:
                if isinstance(item, Mapping):
                    yield from _walk_mappings(item, skip_old_values=skip_old_values)


def _normalize(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 2

    result = build_issue_title_update(event)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
