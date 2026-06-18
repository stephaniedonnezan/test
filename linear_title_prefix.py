"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = frozenset(
    {"status", "statusid", "state", "stateid", "workflowstate", "workflowstateid"}
)


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when an issue moves to the research status."""
    if not isinstance(event, Mapping):
        return None

    context = _event_context(event)
    if not _is_status_change_event(context):
        return None

    status = _new_status(context)
    if _normalize_text(status) != TARGET_STATUS:
        return None

    issue_id = _clean_string(_first_value(context, ("issueId", "issue_id", "identifier", "key", "id")))
    title = _clean_string(_first_value(context, ("title", "name")))
    if not issue_id or not title or _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _event_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten common automation and Linear webhook containers without losing metadata."""
    context: dict[str, Any] = {}

    def merge(value: Any) -> None:
        if isinstance(value, Mapping):
            context.update(value)

    merge(event.get("issue"))

    data = event.get("data")
    if isinstance(data, Mapping):
        merge(data.get("issue"))
        merge(data)

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        merge(trigger_context.get("issue"))
        merge(trigger_context)

    merge(event)
    return context


def _is_status_change_event(context: Mapping[str, Any]) -> bool:
    event_names = [
        _normalize_text(value)
        for key in ("trigger", "webhookType", "action", "type", "event", "eventType")
        if (value := context.get(key)) is not None
    ]
    if any(name in {"status changed", "status change", "issue status changed"} for name in event_names):
        return True

    if any(name in {"update", "updated", "issue update", "issue updated", "updated issue"} for name in event_names):
        return _mentions_status_change(context)

    return _mentions_status_change(context)


def _mentions_status_change(context: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        if _contains_status_field(context.get(key)):
            return True

    for key in ("changes", "changed", "updatedFrom", "updated_from"):
        value = context.get(key)
        if isinstance(value, Mapping) and _contains_status_field(value.keys()):
            return True

    return any(key in context for key in ("newStatus", "new_status", "statusName", "stateName", "workflowStateName"))


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, Mapping):
        items: Sequence[Any] = tuple(value.keys())
    elif isinstance(value, str):
        items = (value,)
    elif isinstance(value, Sequence):
        items = value
    else:
        return False

    return any(_normalize_field_name(item) in STATUS_FIELDS for item in items)


def _new_status(context: Mapping[str, Any]) -> Any:
    for key in ("newStatus", "new_status", "statusName", "stateName", "workflowStateName"):
        if (value := context.get(key)) is not None:
            return value

    for key in ("changes", "changed"):
        value = context.get(key)
        if isinstance(value, Mapping):
            status = _status_from_change_mapping(value)
            if status is not None:
                return status

    return _first_value(context, ("status", "state", "workflowState", "workflow_state"))


def _status_from_change_mapping(changes: Mapping[str, Any]) -> Any:
    for key, value in changes.items():
        if _normalize_field_name(key) not in STATUS_FIELDS:
            continue

        if isinstance(value, Mapping):
            for candidate in ("to", "new", "after", "newValue", "new_value", "name"):
                if (status := value.get(candidate)) is not None:
                    return status
        return value

    return None


def _first_value(context: Mapping[str, Any], keys: Sequence[str]) -> Any:
    for key in keys:
        if key not in context:
            continue

        value = context[key]
        if isinstance(value, Mapping):
            for nested_key in ("name", "title", "identifier", "key", "id"):
                if (nested := value.get(nested_key)) is not None:
                    return nested
        else:
            return value

    return None


def _clean_string(value: Any) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    return text or None


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def _normalize_text(value: Any) -> str:
    if isinstance(value, Mapping):
        value = _first_value(value, ("name", "title", "label", "value", "id"))
    if value is None:
        return ""

    text = str(value).strip()
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def _normalize_field_name(value: Any) -> str:
    return _normalize_text(value).replace(" ", "")


def main() -> int:
    """Read an event JSON document from stdin and print the update action."""
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 2

    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
