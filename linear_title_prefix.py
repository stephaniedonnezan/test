"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
UPDATE_ACTION = "update_issue_title"
STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow_state"}
STATUS_CHANGED_TRIGGERS = {
    "statuschanged",
    "statuschange",
    "statuschangedissue",
    "issue status changed",
    "status changed",
}
ISSUE_UPDATED_TRIGGERS = {
    "issueupdated",
    "updatedissue",
    "update",
    "updated",
    "issue update",
    "issue updated",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update when an issue moves to "to research"."""

    if not isinstance(event, Mapping):
        return None

    context = _event_context(event)
    if not _is_status_change(context):
        return None

    status = _new_status(context)
    if _normalize_status(status) != "to research":
        return None

    issue_id = _issue_id(context)
    title = _issue_title(context)
    if not issue_id or not title:
        return None

    if _has_prefix(title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _event_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten common Cursor automation and Linear webhook payload shapes."""

    context: dict[str, Any] = {}

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        context.update(trigger_context)

    data = event.get("data")
    if isinstance(data, Mapping):
        context.update({key: value for key, value in data.items() if key != "issue"})
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            context.update(issue)

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        context.update(issue)

    context.update(event)
    if isinstance(trigger_context, Mapping):
        # Automation metadata should win over same-named issue fields like "status".
        context.update(trigger_context)
    return context


def _is_status_change(context: Mapping[str, Any]) -> bool:
    trigger_values = [
        context.get("trigger"),
        context.get("webhookType"),
        context.get("action"),
        context.get("type"),
    ]
    normalized_triggers = {
        _normalize_event_type(value) for value in trigger_values if value is not None
    }

    if normalized_triggers & STATUS_CHANGED_TRIGGERS:
        return True

    if normalized_triggers & ISSUE_UPDATED_TRIGGERS:
        return _updated_status_field(context)

    return _updated_status_field(context)


def _updated_status_field(context: Mapping[str, Any]) -> bool:
    updated_fields = context.get("updatedFields")
    if updated_fields is None:
        updated_fields = context.get("updated_fields")

    if _contains_status_field(updated_fields):
        return True

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        return any(_normalize_field_name(field) in STATUS_FIELD_NAMES for field in changes)

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_field_name(value) in STATUS_FIELD_NAMES
    if isinstance(value, Mapping):
        return any(_contains_status_field(key) for key in value)
    if isinstance(value, list | tuple | set):
        return any(_contains_status_field(item) for item in value)
    return False


def _new_status(context: Mapping[str, Any]) -> str | None:
    for key in (
        "newStatus",
        "new_status",
        "toStatus",
        "to_status",
        "statusName",
        "status_name",
    ):
        value = _string_or_name(context.get(key))
        if value:
            return value

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        for field, change in changes.items():
            if _normalize_field_name(field) in STATUS_FIELD_NAMES:
                changed_value = _changed_value(change)
                if changed_value:
                    return changed_value

    for key in ("status", "state", "workflowState", "workflow_state"):
        value = _string_or_name(context.get(key))
        if value:
            return value

    return None


def _changed_value(change: Any) -> str | None:
    if isinstance(change, Mapping):
        for key in ("newValue", "new_value", "to", "after", "value", "name"):
            value = _string_or_name(change.get(key))
            if value:
                return value
    return _string_or_name(change)


def _string_or_name(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            nested = _string_or_name(value.get(key))
            if nested:
                return nested
    return None


def _issue_id(context: Mapping[str, Any]) -> str | None:
    for key in ("issueId", "issue_id", "identifier", "key", "id"):
        value = context.get(key)
        if isinstance(value, str):
            stripped = value.strip()
            if stripped:
                return stripped
    return None


def _issue_title(context: Mapping[str, Any]) -> str | None:
    value = context.get("title")
    if isinstance(value, str):
        stripped = value.strip()
        if stripped:
            return stripped
    return None


def _normalize_status(value: str | None) -> str | None:
    if value is None:
        return None
    words = _words(value)
    return " ".join(words) if words else None


def _normalize_event_type(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(_words(value))


def _normalize_field_name(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return "".join(_words(value))


def _words(value: str) -> list[str]:
    expanded = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    return re.findall(r"[a-z0-9]+", expanded.lower())


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        json.dump(update, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
