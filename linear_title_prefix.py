"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


RESEARCH_STATUS = "to research"
TITLE_PREFIX = "Cursor researching"
UPDATE_ACTION = "update_issue_title"

_STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}
_STATUS_CHANGE_TRIGGERS = {
    "statuschanged",
    "statuschange",
    "statusupdated",
    "statusupdate",
    "statechanged",
    "statechange",
    "workflowstatechanged",
    "workflowstatechange",
}
_ISSUE_UPDATE_TRIGGERS = {
    "issueupdated",
    "updatedissue",
    "update",
    "updated",
}


def build_issue_title_update(event: Any) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to research."""

    context = _event_context(event)
    if not context or not _is_status_change(context):
        return None

    if _normalize_status(_new_status(context)) != RESEARCH_STATUS:
        return None

    issue_id = _first_text(context, ("issueId", "issue_id", "id", "identifier", "key"))
    title = _first_text(context, ("title", "name"))
    if not issue_id or not title or _has_research_prefix(title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def handle_issue_status_changed(event: Any) -> dict[str, str] | None:
    """Compatibility alias for automation callers using event-style naming."""

    return build_issue_title_update(event)


def _event_context(event: Any) -> dict[str, Any] | None:
    if not isinstance(event, Mapping):
        return None

    context: dict[str, Any] = {}

    for container_key in ("issue", "data", "triggerContext", "webhook"):
        nested = event.get(container_key)
        if isinstance(nested, Mapping):
            context.update(_event_context(nested) or {})

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            context.update(_event_context(issue) or {})

    context.update(dict(event))
    return context


def _is_status_change(context: Mapping[str, Any]) -> bool:
    trigger_values = (
        context.get("trigger"),
        context.get("action"),
        context.get("type"),
        context.get("webhookType"),
        context.get("eventType"),
    )

    if any(_normalize_token(value) in _STATUS_CHANGE_TRIGGERS for value in trigger_values):
        return True

    if any(_normalize_token(value) in _ISSUE_UPDATE_TRIGGERS for value in trigger_values):
        return _updated_fields_include_status(context)

    return False


def _updated_fields_include_status(context: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        fields = context.get(key)
        if isinstance(fields, str):
            candidates = [fields]
        elif isinstance(fields, Mapping):
            candidates = fields
        elif isinstance(fields, (list, tuple, set)):
            candidates = fields
        else:
            continue

        if any(_normalize_field_name(field) in _STATUS_FIELDS for field in candidates):
            return True

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        return any(_normalize_field_name(field) in _STATUS_FIELDS for field in changes)

    return False


def _new_status(context: Mapping[str, Any]) -> Any:
    for key in ("newStatus", "new_status", "statusName", "status_name"):
        value = context.get(key)
        if _has_text(value):
            return value

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        for key in ("status", "state", "workflowState", "workflow_state"):
            value = _changed_value(changes.get(key))
            if _has_text(value):
                return value

    for key in ("status", "state", "workflowState", "workflow_state"):
        value = context.get(key)
        if isinstance(value, Mapping):
            for name_key in ("name", "title", "status"):
                nested_value = value.get(name_key)
                if _has_text(nested_value):
                    return nested_value
        elif _has_text(value):
            return value

    return None


def _changed_value(value: Any) -> Any:
    if not isinstance(value, Mapping):
        return value

    for key in ("newValue", "new_value", "to", "after", "name"):
        candidate = value.get(key)
        if isinstance(candidate, Mapping):
            nested_name = candidate.get("name")
            if _has_text(nested_name):
                return nested_name
        elif _has_text(candidate):
            return candidate

    return None


def _first_text(context: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = context.get(key)
        if _has_text(value):
            return str(value).strip()
    return None


def _has_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _has_research_prefix(title: str) -> bool:
    return re.match(rf"^\s*{re.escape(TITLE_PREFIX)}\b", title, re.IGNORECASE) is not None


def _normalize_status(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    normalized = re.sub(r"[_-]+", " ", value)
    normalized = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip().lower()


def _normalize_token(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _normalize_field_name(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return _normalize_token(value)


def main() -> int:
    """Read a JSON event from stdin and print the update action when needed."""

    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
