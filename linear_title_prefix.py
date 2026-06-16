"""Build Linear issue title updates for the "to research" status.

The automation platform is expected to apply the returned action to Linear.
This module intentionally keeps side effects out of the handler so it can be
tested with representative webhook payloads.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "state id",
    "state name",
    "workflow state",
    "workflow state id",
    "workflow state name",
}

_STATUS_CHANGE_TRIGGERS = {
    "status changed",
    "status change",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
}

_ISSUE_UPDATE_EVENTS = {
    "issue update",
    "issue updated",
    "updated issue",
    "update issue",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title-update action when an issue moves to "to research".

    The handler accepts both Cursor's flat trigger context payloads and common
    Linear webhook shapes with nested ``data``/``issue`` objects. It returns
    ``None`` when the event is unrelated, lacks required issue data, or the
    title already carries the research prefix.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = list(_contexts(event))
    if not _is_status_change_event(contexts):
        return None

    status = _extract_status(contexts)
    if _normalize_words(status) != TARGET_STATUS:
        return None

    title = _clean_string(_first_value(contexts, ("title", "name")))
    if not title or _has_research_prefix(title):
        return None

    issue_id = _extract_issue_id(contexts)
    if not issue_id:
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield useful mappings from broad metadata to nested issue data."""

    yield event

    for key in ("triggerContext", "payload", "webhook", "data", "issue"):
        value = event.get(key)
        if isinstance(value, Mapping):
            yield value

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            yield issue

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        for key in ("data", "issue"):
            value = trigger_context.get(key)
            if isinstance(value, Mapping):
                yield value


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    event_markers: list[str] = []
    for context in contexts:
        for key in ("trigger", "webhookType", "action", "type", "event", "eventType"):
            marker = _clean_string(context.get(key))
            if marker:
                event_markers.append(marker)

    normalized_markers = {_normalize_words(marker) for marker in event_markers}
    if normalized_markers & _STATUS_CHANGE_TRIGGERS:
        return True

    is_issue_update = bool(normalized_markers & _ISSUE_UPDATE_EVENTS)
    is_issue_update = is_issue_update or (
        "update" in normalized_markers and "issue" in normalized_markers
    )
    return is_issue_update and _status_field_was_updated(contexts)


def _status_field_was_updated(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in (
            "updatedFields",
            "changedFields",
            "changed_fields",
            "updated_fields",
            "fields",
        ):
            if _contains_status_field(context.get(key)):
                return True

        for key in ("changes", "changed", "updatedFrom", "updated_from"):
            if _contains_status_field_marker(context.get(key)):
                return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_words(value) in _STATUS_FIELD_NAMES

    if isinstance(value, Mapping):
        return any(_normalize_words(key) in _STATUS_FIELD_NAMES for key in value)

    if isinstance(value, Iterable):
        return any(_contains_status_field(item) for item in value)

    return False


def _contains_status_field_marker(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if _normalize_words(key) in _STATUS_FIELD_NAMES:
                return True
            if _contains_status_field_marker(nested):
                return True
        return False

    if isinstance(value, list):
        return any(_contains_status_field_marker(item) for item in value)

    return False


def _extract_status(contexts: list[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        status = _first_value(
            [context],
            (
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
            ),
        )
        if _clean_string(status):
            return _clean_string(status)

    changed_status = _extract_status_from_changes(contexts)
    if changed_status:
        return changed_status

    for context in contexts:
        direct_status = _clean_string(context.get("status"))
        if direct_status:
            return direct_status

        for key in ("state", "workflowState", "workflow_state"):
            value = context.get(key)
            if isinstance(value, Mapping):
                nested_name = _clean_string(
                    _first_value([value], ("name", "title", "status", "state"))
                )
                if nested_name:
                    return nested_name
            elif _clean_string(value):
                return _clean_string(value)

    return None


def _extract_status_from_changes(contexts: list[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        for key in ("changes", "changed"):
            value = context.get(key)
            if isinstance(value, Mapping):
                status = _status_value_from_change_mapping(value)
                if status:
                    return status
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, Mapping):
                        status = _status_value_from_change_mapping(item)
                        if status:
                            return status
    return None


def _status_value_from_change_mapping(change: Mapping[str, Any]) -> str | None:
    for key, value in change.items():
        if _normalize_words(key) not in _STATUS_FIELD_NAMES:
            continue

        if isinstance(value, Mapping):
            for new_key in ("to", "new", "newValue", "new_value", "after", "name"):
                status = _clean_string(value.get(new_key))
                if status:
                    return status
        else:
            status = _clean_string(value)
            if status:
                return status

    return None


def _extract_issue_id(contexts: list[Mapping[str, Any]]) -> str | None:
    preferred_keys = ("issueId", "issue_id", "identifier", "key")
    issue_id = _clean_string(_first_value(contexts, preferred_keys))
    if issue_id:
        return issue_id

    for context in contexts:
        if _looks_like_issue_context(context):
            issue_id = _clean_string(context.get("id"))
            if issue_id:
                return issue_id

    return None


def _looks_like_issue_context(context: Mapping[str, Any]) -> bool:
    return any(key in context for key in ("title", "identifier", "state", "workflowState"))


def _first_value(contexts: Iterable[Mapping[str, Any]], keys: tuple[str, ...]) -> Any:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if value is not None:
                return value
    return None


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def _clean_string(value: Any) -> str | None:
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    return None


def _normalize_words(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    camel_spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    words = re.sub(r"[^A-Za-z0-9]+", " ", camel_spaced).lower().split()
    return " ".join(words)


def main() -> int:
    """Read a JSON event from stdin and print the computed action."""

    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(build_issue_title_update(event), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
