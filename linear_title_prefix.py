"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow state"}
STATUS_CHANGE_TRIGGERS = {
    "status changed",
    "status change",
    "statuschanged",
    "state changed",
    "workflow state changed",
}
ISSUE_UPDATE_TRIGGERS = {
    "issue updated",
    "updated issue",
    "update",
    "updated",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue-title update action when a Linear issue enters research."""

    if not isinstance(event, Mapping):
        return None

    context = _event_context(event)
    if not _is_status_change_event(context):
        return None

    status = _new_status(context)
    if _normalize_status(status) != RESEARCH_STATUS:
        return None

    issue_id = _first_text(context, ("id", "issueId", "issue_id", "identifier", "key"))
    title = _first_text(context, ("title", "name"))
    if not issue_id or not title:
        return None

    if title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _event_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten common Linear automation and webhook wrappers into one context."""

    context: dict[str, Any] = {}
    _merge_mapping(context, event.get("issue"))

    data = event.get("data")
    if isinstance(data, Mapping):
        _merge_mapping(context, data.get("issue"))
        _merge_mapping(context, data)

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        _merge_mapping(context, trigger_context.get("issue"))
        _merge_mapping(context, trigger_context)

    _merge_mapping(context, event)
    return context


def _merge_mapping(target: dict[str, Any], value: Any) -> None:
    if isinstance(value, Mapping):
        target.update(value)


def _is_status_change_event(context: Mapping[str, Any]) -> bool:
    trigger_names = _normalized_trigger_names(context)
    if trigger_names & STATUS_CHANGE_TRIGGERS:
        return True

    if trigger_names & ISSUE_UPDATE_TRIGGERS:
        return _mentions_status_field(context)

    return False


def _normalized_trigger_names(context: Mapping[str, Any]) -> set[str]:
    names = set()
    for key in ("trigger", "webhookType", "action", "type"):
        value = context.get(key)
        if isinstance(value, str):
            names.add(_normalize_words(value))
    return names


def _mentions_status_field(context: Mapping[str, Any]) -> bool:
    updated_fields = context.get("updatedFields")
    if _contains_status_name(updated_fields):
        return True

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        return any(_normalize_field_name(key) in STATUS_FIELD_NAMES for key in changes)

    return False


def _contains_status_name(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_field_name(value) in STATUS_FIELD_NAMES

    if isinstance(value, Mapping):
        return any(_contains_status_name(key) or _contains_status_name(item) for key, item in value.items())

    if isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray)):
        return any(_contains_status_name(item) for item in value)

    return False


def _new_status(context: Mapping[str, Any]) -> str | None:
    for key in ("newStatus", "new_status", "statusName", "stateName", "workflowStateName"):
        value = _text_or_name(context.get(key))
        if value:
            return value

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        for key in ("status", "state", "workflowState", "workflow_state"):
            value = _changed_value(changes.get(key))
            if value:
                return value

    for key in ("status", "state", "workflowState", "workflow_state"):
        value = _text_or_name(context.get(key))
        if value:
            return value

    return None


def _changed_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("to", "new", "newValue", "after", "name"):
            result = _text_or_name(value.get(key))
            if result:
                return result
        return None

    return _text_or_name(value)


def _text_or_name(value: Any) -> str | None:
    if isinstance(value, str):
        text = value.strip()
        return text or None

    if isinstance(value, Mapping):
        return _text_or_name(value.get("name"))

    return None


def _first_text(context: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = _text_or_name(context.get(key))
        if value:
            return value
    return None


def _normalize_status(value: str | None) -> str | None:
    if value is None:
        return None
    return _normalize_words(value)


def _normalize_words(value: str) -> str:
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    normalized = re.sub(r"[^a-zA-Z0-9]+", " ", spaced)
    return " ".join(normalized.casefold().split())


def _normalize_field_name(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return _normalize_words(value)


def main() -> int:
    """Read a JSON event from stdin and print the title-update action, if any."""

    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
