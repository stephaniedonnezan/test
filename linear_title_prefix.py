"""Build Linear issue title updates for research status changes.

The automation runner can pass Linear webhook data in a few shapes depending on
the trigger source. This module keeps the decision logic small and pure: given a
payload, return the title update action the runner should perform, or ``None``.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


RESEARCH_STATUS = "to research"
TITLE_PREFIX = "Cursor researching"

_STATUS_FIELDS = {"status", "state", "workflowstate", "workflow state"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue enters research."""

    if not isinstance(event, Mapping):
        return None

    context = _flatten_event(event)
    if not _is_status_change(context):
        return None

    new_status = _new_status(context)
    if _normalize_text(new_status) != RESEARCH_STATUS:
        return None

    issue_id = _issue_id(context)
    title = _issue_title(context)
    if not issue_id or not title:
        return None

    if title.lower().startswith(TITLE_PREFIX.lower()):
        updated_title = title
    else:
        updated_title = f"{TITLE_PREFIX}: {title}"

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": updated_title,
    }


def _flatten_event(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common Linear payload containers into one lookup dictionary."""

    context: dict[str, Any] = {}
    for key in ("triggerContext", "trigger_context", "webhook", "data", "issue"):
        value = event.get(key)
        if isinstance(value, Mapping):
            context.update(_flatten_event(value))

    context.update(event)
    return context


def _is_status_change(context: Mapping[str, Any]) -> bool:
    trigger_values = (
        context.get("trigger"),
        context.get("webhookType"),
        context.get("webhook_type"),
        context.get("action"),
        context.get("type"),
    )
    normalized_triggers = {_normalize_text(value) for value in trigger_values if value}

    if normalized_triggers & {"status changed", "status change", "status updated"}:
        return True

    if normalized_triggers & {"issue updated", "updated issue", "update", "updated"}:
        return _updated_status_field(context.get("updatedFields")) or _updated_status_field(
            context.get("updated_fields")
        )

    return False


def _updated_status_field(updated_fields: Any) -> bool:
    if isinstance(updated_fields, str):
        fields = [updated_fields]
    elif isinstance(updated_fields, Mapping):
        fields = list(updated_fields.keys())
    elif isinstance(updated_fields, list | tuple | set):
        fields = list(updated_fields)
    else:
        return False

    for field in fields:
        field_name = _normalize_text(_field_name(field))
        if field_name in _STATUS_FIELDS:
            return True
    return False


def _new_status(context: Mapping[str, Any]) -> str | None:
    for key in ("newStatus", "new_status", "statusName", "status_name"):
        value = _string_value(context.get(key))
        if value:
            return value

    for key in ("status", "state", "workflowState", "workflow_state"):
        value = context.get(key)
        if isinstance(value, Mapping):
            name = _string_value(value.get("name"))
            if name:
                return name
        else:
            name = _string_value(value)
            if name:
                return name

    return None


def _issue_id(context: Mapping[str, Any]) -> str | None:
    for key in ("issueId", "issue_id", "id", "identifier"):
        value = _string_value(context.get(key))
        if value:
            return value
    return None


def _issue_title(context: Mapping[str, Any]) -> str | None:
    return _string_value(context.get("title"))


def _field_name(field: Any) -> Any:
    if isinstance(field, Mapping):
        return field.get("name") or field.get("field") or field.get("key")
    return field


def _string_value(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    stripped = value.strip()
    return stripped or None


def _normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value.strip())
    return re.sub(r"[\s_-]+", " ", spaced).casefold()


def main() -> int:
    payload = json.load(sys.stdin)
    action = build_issue_title_update(payload)
    if action is not None:
        print(json.dumps(action))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
