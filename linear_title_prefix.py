"""Build Linear issue title update actions for research-status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update action when an issue moves to To Research."""
    if not isinstance(event, Mapping):
        return None

    context = _payload_context(event)
    if not _is_status_change_event(context):
        return None

    status = _changed_status(context)
    if _normalize_text(status) != _normalize_text(TARGET_STATUS):
        return None

    issue_id = _first_text(context, ("issueId", "issue_id", "id", "identifier", "key"))
    title = _first_text(context, ("title", "name"))
    if issue_id is None or title is None:
        return None

    title = title.strip()
    if _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _payload_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge nested Linear issue data with outer automation metadata."""
    context: dict[str, Any] = {}

    for path in (
        ("data", "issue"),
        ("issue",),
        ("triggerContext", "data", "issue"),
        ("triggerContext", "issue"),
    ):
        nested = _get_mapping(event, path)
        if nested is not None:
            context.update(nested)

    for path in (("data",), ("triggerContext",)):
        nested = _get_mapping(event, path)
        if nested is not None:
            context.update(nested)

    context.update(event)
    return context


def _is_status_change_event(context: Mapping[str, Any]) -> bool:
    event_names = [
        value
        for key in ("trigger", "webhookType", "action", "type", "event")
        if (value := context.get(key)) is not None
    ]

    if any(_normalize_text(value) in {"status changed", "statuschanged"} for value in event_names):
        return True

    if any(_normalize_text(value) in {"issue updated", "updated issue", "update"} for value in event_names):
        return _has_status_field(context.get("updatedFields")) or _has_status_field(context.get("changes"))

    return False


def _changed_status(context: Mapping[str, Any]) -> Any:
    for key in ("newStatus", "new_status", "statusName", "stateName", "workflowStateName"):
        if context.get(key) is not None:
            return context[key]

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        for key in ("status", "state", "workflowState", "workflow_state"):
            changed = changes.get(key)
            if isinstance(changed, Mapping):
                for changed_key in ("newValue", "new_value", "to", "after", "name"):
                    if changed.get(changed_key) is not None:
                        return changed[changed_key]
            elif changed is not None:
                return changed

    for key in ("status", "state", "workflowState", "workflow_state"):
        value = context.get(key)
        if isinstance(value, Mapping):
            for nested_key in ("name", "title"):
                if value.get(nested_key) is not None:
                    return value[nested_key]
        elif value is not None:
            return value

    return None


def _has_status_field(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(_normalize_field(key) in STATUS_FIELDS for key in value)

    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return any(_normalize_field(item) in STATUS_FIELDS for item in value)

    return _normalize_field(value) in STATUS_FIELDS


def _first_text(context: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = context.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _get_mapping(event: Mapping[str, Any], path: tuple[str, ...]) -> Mapping[str, Any] | None:
    value: Any = event
    for key in path:
        if not isinstance(value, Mapping):
            return None
        value = value.get(key)
    return value if isinstance(value, Mapping) else None


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def _normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    value = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    value = re.sub(r"[_\-\s]+", " ", value)
    return value.strip().lower()


def _normalize_field(value: Any) -> str:
    return re.sub(r"[^a-z]", "", _normalize_text(value))


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
