"""Build Linear issue title updates for issues entering research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to To Research.

    The automation trigger can provide a flat ``triggerContext`` payload, while
    Linear webhooks commonly nest issue details under ``data`` or ``issue``.
    This function accepts both shapes and leaves non-matching events untouched.
    """

    if not isinstance(event, Mapping):
        return None

    context = _flatten_event(event)
    if not _is_status_change_event(event, context):
        return None

    if _normalize_status(_first_value(context, ("newStatus", "new_status", "status"))) != TARGET_STATUS:
        status = _status_from_nested_issue(context)
        if _normalize_status(status) != TARGET_STATUS:
            return None

    issue_id = _string_value(_first_value(context, ("id", "issueId", "issue_id", "identifier")))
    title = _string_value(context.get("title"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def handle_issue_status_changed(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Compatibility wrapper for JavaScript-style automation naming."""

    return build_issue_title_update(event)


def _flatten_event(event: Mapping[str, Any]) -> dict[str, Any]:
    context: dict[str, Any] = {}

    for key in ("issue", "data"):
        value = event.get(key)
        if isinstance(value, Mapping):
            context.update(value)

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        for key in ("issue", "data"):
            value = trigger_context.get(key)
            if isinstance(value, Mapping):
                context.update(value)
        context.update(trigger_context)

    context.update(event)
    return context


def _is_status_change_event(event: Mapping[str, Any], context: Mapping[str, Any]) -> bool:
    for key in ("trigger", "webhookType"):
        if _normalize_event_type(context.get(key)) in {"status changed", "status"}:
            return True

    event_types = [
        _normalize_event_type(value)
        for value in _walk_values(event, ("trigger", "webhookType", "action", "type"))
    ]

    if any(value in {"status changed", "status"} for value in event_types):
        return True

    if any(value in {"update", "updated", "issue updated", "updated issue"} for value in event_types):
        return _updated_fields_include_status(event)

    return False


def _updated_fields_include_status(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, nested_value in value.items():
            normalized_key = _normalize_event_type(key)
            if normalized_key in {"updated fields", "updated from", "changed fields", "changes"}:
                if _contains_status_field(nested_value):
                    return True
            if _updated_fields_include_status(nested_value):
                return True
    elif isinstance(value, list):
        return any(_updated_fields_include_status(item) for item in value)

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_event_type(value) in {"status", "state", "workflow state"}
    if isinstance(value, Mapping):
        return any(
            _normalize_event_type(key) in {"status", "state", "workflow state"}
            or _contains_status_field(nested_value)
            for key, nested_value in value.items()
        )
    if isinstance(value, list):
        return any(_contains_status_field(item) for item in value)
    return False


def _status_from_nested_issue(context: Mapping[str, Any]) -> Any:
    for key in ("state", "workflowState", "workflow_state", "status"):
        value = context.get(key)
        if isinstance(value, Mapping):
            name = value.get("name")
            if name is not None:
                return name
        elif value is not None:
            return value
    return None


def _walk_values(value: Any, keys: tuple[str, ...]) -> list[Any]:
    values: list[Any] = []
    if isinstance(value, Mapping):
        for key, nested_value in value.items():
            if key in keys:
                values.append(nested_value)
            values.extend(_walk_values(nested_value, keys))
    elif isinstance(value, list):
        for item in value:
            values.extend(_walk_values(item, keys))
    return values


def _first_value(context: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = context.get(key)
        if value is not None:
            return value
    return None


def _string_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return str(value).strip() or None


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def _normalize_status(value: Any) -> str | None:
    normalized = _normalize_words(value)
    return normalized if normalized else None


def _normalize_event_type(value: Any) -> str | None:
    normalized = _normalize_words(value)
    return normalized if normalized else None


def _normalize_words(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    value = re.sub(r"[^A-Za-z0-9]+", " ", value)
    return " ".join(value.lower().split())


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
