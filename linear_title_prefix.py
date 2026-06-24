"""Build Linear issue title updates for research-status automation.

The automation runner can pipe a Linear/Cursor event into this module.  When
the event is an issue status change to "to research", the handler returns a
small action payload asking the caller to prefix the issue title.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
ACTION = "update_issue_title"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {"status", "state", "workflowstate"}
_DIRECT_STATUS_CHANGE_TRIGGERS = {
    "status changed",
    "status change",
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
_TRIGGER_KEYS = {"trigger", "webhooktype", "webhookevent", "eventtype", "action", "type"}
_EXPLICIT_NEW_STATUS_KEYS = {
    "newstatus",
    "newstatusname",
    "newstate",
    "newstatename",
    "newworkflowstate",
    "newworkflowstatename",
}
_CURRENT_STATUS_KEYS = {"status", "state", "workflowstate"}
_ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "key", "id")
_TITLE_KEYS = ("title", "name")


def build_issue_title_update(event: Any) -> dict[str, str] | None:
    """Return an issue title update action for matching Linear events.

    The returned shape is intentionally small so the surrounding automation can
    decide how to perform the Linear API update.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    if _normalize_text(_extract_new_status(event)) != TARGET_STATUS:
        return None

    issue_id = _first_string(event, _ISSUE_ID_KEYS)
    title = _first_string(event, _TITLE_KEYS)
    if not issue_id or not title:
        return None

    clean_title = title.strip()
    if not clean_title or clean_title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": ACTION,
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {clean_title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    trigger_values = [
        _normalize_text(value)
        for key, value in _walk_items(event)
        if _normalize_key(key) in _TRIGGER_KEYS and isinstance(value, str)
    ]

    if any(value in _DIRECT_STATUS_CHANGE_TRIGGERS for value in trigger_values):
        return True

    return any(value in _UPDATE_TRIGGERS for value in trigger_values) and _has_status_changed_field(event)


def _has_status_changed_field(event: Mapping[str, Any]) -> bool:
    for key, value in _walk_items(event):
        normalized_key = _normalize_key(key)
        if normalized_key == "updatedfields" and _contains_status_field(value):
            return True
        if normalized_key in {"changes", "changedfields", "updatedfrom"}:
            if isinstance(value, Mapping) and any(_is_status_field(field) for field in value):
                return True
            if _contains_status_field(value):
                return True

    return False


def _extract_new_status(event: Mapping[str, Any]) -> Any:
    explicit = _first_value(event, _EXPLICIT_NEW_STATUS_KEYS)
    if explicit is not None:
        return explicit

    changed_status = _status_from_change_metadata(event)
    if changed_status is not None:
        return changed_status

    return _first_value(event, _CURRENT_STATUS_KEYS)


def _status_from_change_metadata(event: Mapping[str, Any]) -> Any:
    for key, value in _walk_items(event):
        if _normalize_key(key) not in {"changes", "changedfields"} or not isinstance(value, Mapping):
            continue

        for field_name, change in value.items():
            if not _is_status_field(field_name):
                continue
            if isinstance(change, Mapping):
                for new_key in ("newValue", "new_value", "to", "after", "new", "name"):
                    if new_key in change:
                        return _status_name(change[new_key])
            return _status_name(change)

    return None


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)
    if isinstance(value, Mapping):
        return any(_is_status_field(key) or _contains_status_field(item) for key, item in value.items())
    if isinstance(value, Iterable):
        return any(_contains_status_field(item) for item in value)
    return False


def _is_status_field(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    return _normalize_key(value) in _STATUS_FIELD_NAMES


def _first_string(event: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    value = _first_value(event, {_normalize_key(key) for key in keys})
    return value.strip() if isinstance(value, str) else None


def _first_value(event: Mapping[str, Any], normalized_keys: Iterable[str]) -> Any:
    wanted = set(normalized_keys)
    for context in _candidate_contexts(event):
        for key, value in context.items():
            if isinstance(key, str) and _normalize_key(key) in wanted:
                status_value = _status_name(value)
                if status_value is not None:
                    return status_value
    return None


def _candidate_contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely issue contexts before broader webhook containers."""

    trigger_context = event.get("triggerContext")
    data = event.get("data")
    issue = event.get("issue")

    contexts: list[Mapping[str, Any]] = []
    for value in (trigger_context,):
        if isinstance(value, Mapping):
            contexts.append(value)
    if isinstance(trigger_context, Mapping) and isinstance(trigger_context.get("issue"), Mapping):
        contexts.append(trigger_context["issue"])
    if isinstance(issue, Mapping):
        contexts.append(issue)
    if isinstance(data, Mapping) and isinstance(data.get("issue"), Mapping):
        contexts.append(data["issue"])
    for value in (event, data):
        if isinstance(value, Mapping):
            contexts.append(value)

    seen: set[int] = set()
    for context in contexts:
        if id(context) in seen:
            continue
        seen.add(id(context))
        yield context


def _walk_items(value: Any) -> Iterable[tuple[str, Any]]:
    if not isinstance(value, Mapping):
        return

    for key, item in value.items():
        if isinstance(key, str):
            yield key, item
        if isinstance(item, Mapping):
            yield from _walk_items(item)
        elif isinstance(item, list):
            for list_item in item:
                yield from _walk_items(list_item)


def _status_name(value: Any) -> Any:
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            if key in value:
                return value[key]
    return value


def _normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    value = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    value = re.sub(r"[^A-Za-z0-9]+", " ", value)
    return " ".join(value.lower().split())


def _normalize_key(value: Any) -> str:
    return _normalize_text(value).replace(" ", "")


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON input: {exc}", file=sys.stderr)
        return 1

    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
