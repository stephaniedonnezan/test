"""Build Linear issue title updates for research status changes.

The automation runner can pass either Cursor's flat ``triggerContext`` payload
or a nested Linear webhook payload. This module keeps the decision pure: callers
can apply the returned update action with their Linear client.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


TITLE_MARKER = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow state"}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to research.

    The returned shape is intentionally small and side-effect free:
    ``{"action": "update_issue_title", "issueId": "...", "title": "..."}``.
    ``None`` means the event should not change the issue title.
    """

    if not isinstance(event, Mapping):
        return None

    context = _event_context(event)
    if not _is_status_change_event(context):
        return None

    new_status = _new_status(context)
    if _normalize_name(new_status) != TARGET_STATUS:
        return None

    issue_id = _issue_id(context)
    title = _issue_title(context)
    if not issue_id or not title:
        return None

    if _has_title_marker(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_MARKER}: {title}",
    }


def _event_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common Linear/Cursor payload locations into one lookup context."""

    context: dict[str, Any] = {}

    for path in (
        ("data", "issue"),
        ("issue",),
        ("triggerContext", "issue"),
        ("triggerContext",),
        ("data",),
        (),
    ):
        value = _get_path(event, path)
        if isinstance(value, Mapping):
            context.update(value)

    # Keep selected nested objects available for status/title/id fallbacks.
    for key in ("state", "status", "workflowState", "workflow_state"):
        value = _first_mapping_at(event, key)
        if value is not None and key not in context:
            context[key] = value

    for key in ("changes", "updatedFields", "updated_fields"):
        value = _first_value_at(event, key)
        if value is not None and key not in context:
            context[key] = value

    return context


def _is_status_change_event(context: Mapping[str, Any]) -> bool:
    trigger_values = [
        context.get("trigger"),
        context.get("webhookType"),
        context.get("action"),
        context.get("type"),
        context.get("eventType"),
        context.get("event_type"),
    ]
    normalized_triggers = {_normalize_name(value) for value in trigger_values if value}

    if any(
        trigger in normalized_triggers
        for trigger in ("status changed", "status change", "state changed", "workflow state changed")
    ):
        return True

    if any(trigger in normalized_triggers for trigger in ("update", "updated", "issue updated", "updated issue")):
        return _updated_fields_include_status(context)

    return False


def _updated_fields_include_status(context: Mapping[str, Any]) -> bool:
    updated_fields = context.get("updatedFields", context.get("updated_fields"))
    for field in _iter_field_names(updated_fields):
        if _normalize_field_name(field) in STATUS_FIELDS:
            return True

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        for field in changes:
            if _normalize_field_name(field) in STATUS_FIELDS:
                return True

    return False


def _new_status(context: Mapping[str, Any]) -> str | None:
    for key in (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "newWorkflowState",
        "new_workflow_state",
    ):
        value = _name_from_value(context.get(key))
        if value:
            return value

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        for key in ("status", "state", "workflowState", "workflow_state"):
            value = _changed_field_new_value(changes.get(key))
            if value:
                return value

    for key in ("status", "state", "workflowState", "workflow_state"):
        value = _name_from_value(context.get(key))
        if value:
            return value

    return None


def _changed_field_new_value(change: Any) -> str | None:
    if isinstance(change, Mapping):
        for key in ("newValue", "new_value", "to", "after", "new"):
            value = _name_from_value(change.get(key))
            if value:
                return value
    return _name_from_value(change)


def _issue_id(context: Mapping[str, Any]) -> str | None:
    for key in ("issueId", "issue_id", "identifier", "key", "id"):
        value = _clean_string(context.get(key))
        if value:
            return value
    return None


def _issue_title(context: Mapping[str, Any]) -> str | None:
    for key in ("title", "name"):
        value = _clean_string(context.get(key))
        if value:
            return value
    return None


def _has_title_marker(title: str) -> bool:
    return title.strip().lower().startswith(TITLE_MARKER.lower())


def _name_from_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            text = _clean_string(value.get(key))
            if text:
                return text
        return None
    return _clean_string(value)


def _iter_field_names(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, Mapping):
        return [str(key) for key in value]
    if isinstance(value, list | tuple | set):
        return [str(item) for item in value]
    return []


def _normalize_name(value: Any) -> str:
    text = _clean_string(value)
    if not text:
        return ""

    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[_\-/]+", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def _normalize_field_name(value: Any) -> str:
    return _normalize_name(value).replace(" ", "")


def _clean_string(value: Any) -> str | None:
    if isinstance(value, str):
        text = value.strip()
        return text or None
    return None


def _get_path(source: Mapping[str, Any], path: tuple[str, ...]) -> Any:
    value: Any = source
    for key in path:
        if not isinstance(value, Mapping):
            return None
        value = value.get(key)
    return value


def _first_value_at(value: Any, key: str) -> Any:
    if isinstance(value, Mapping):
        if key in value:
            return value[key]
        for child in value.values():
            found = _first_value_at(child, key)
            if found is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _first_value_at(child, key)
            if found is not None:
                return found
    return None


def _first_mapping_at(value: Any, key: str) -> Mapping[str, Any] | None:
    found = _first_value_at(value, key)
    if isinstance(found, Mapping):
        return found
    return None


def main() -> int:
    payload = json.load(sys.stdin)
    update = build_issue_title_update(payload)
    if update is None:
        return 0

    json.dump(update, sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
