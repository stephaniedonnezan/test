"""Build title updates for Linear issues entering research status.

The Cursor automation runner supplies Linear issue events with a small flat
`triggerContext` shape, while Linear webhooks can be more nested. This module
keeps the decision logic isolated and dependency-free so it can be exercised by
unit tests and invoked from a thin automation adapter.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {
    "status",
    "statusid",
    "state",
    "stateid",
    "workflowstate",
    "workflowstateid",
    "workflow_state",
    "workflow_state_id",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue title update action when a Linear issue enters research.

    The action is intentionally small and declarative so the surrounding
    automation can perform the Linear write:

    {"action": "update_issue_title", "issueId": "...", "title": "..."}
    """

    if not isinstance(event, Mapping):
        return None

    context = _event_context(event)
    if not _is_status_change_event(context):
        return None

    new_status = _extract_new_status(context)
    if _normalize_status(new_status) != _normalize_status(TARGET_STATUS):
        return None

    issue_id = _extract_issue_id(context)
    title = _extract_title(context)
    if not issue_id or not title:
        return None

    stripped_title = title.strip()
    if _has_prefix(stripped_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {stripped_title}",
    }


def _event_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten the useful parts of known Cursor and Linear payload shapes."""

    merged: dict[str, Any] = {}

    trigger_context = _mapping(event.get("triggerContext"))
    data = _mapping(event.get("data"))
    issue = _mapping(data.get("issue")) or _mapping(event.get("issue"))

    # Linear webhooks usually put the issue directly in data. Some adapters wrap
    # it in data.issue. Keep outer event fields last so explicit trigger metadata
    # such as `newStatus` wins over stale nested issue state.
    for part in (issue, data, trigger_context, event):
        if part:
            merged.update(part)

    if "triggerContext" in merged and isinstance(merged["triggerContext"], Mapping):
        merged.pop("triggerContext", None)

    return merged


def _is_status_change_event(context: Mapping[str, Any]) -> bool:
    trigger_values = [
        context.get("trigger"),
        context.get("webhookType"),
        context.get("action"),
        context.get("type"),
        context.get("eventType"),
    ]
    normalized_values = {_normalize_event_value(value) for value in trigger_values if value}

    if normalized_values & {"statuschanged", "statuschange"}:
        return True
    if "statuschanged" in normalized_values:
        return True

    if normalized_values & {"issueupdated", "update", "updatedissue"}:
        return _updated_fields_include_status(context)

    return False


def _updated_fields_include_status(context: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        fields = context.get(key)
        if isinstance(fields, str):
            candidates = [fields]
        elif isinstance(fields, (list, tuple, set)):
            candidates = fields
        else:
            candidates = []

        for field in candidates:
            if _normalize_field_name(field) in STATUS_FIELDS:
                return True

    changes = context.get("changes") or context.get("updatedFrom")
    if isinstance(changes, Mapping):
        return any(_normalize_field_name(field) in STATUS_FIELDS for field in changes)

    return False


def _extract_new_status(context: Mapping[str, Any]) -> str | None:
    for key in (
        "newStatus",
        "new_status",
        "statusName",
        "status_name",
        "newState",
        "new_state",
        "stateName",
        "state_name",
        "workflowStateName",
        "workflow_state_name",
    ):
        value = _text(context.get(key))
        if value:
            return value

    for key in ("status", "state", "workflowState", "workflow_state"):
        value = context.get(key)
        if isinstance(value, Mapping):
            name = _text(value.get("name"))
            if name:
                return name
        else:
            text = _text(value)
            if text:
                return text

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        for key in ("status", "state", "workflowState", "workflow_state"):
            change = changes.get(key)
            if isinstance(change, Mapping):
                new_value = change.get("new") or change.get("to") or change.get("newValue")
                if isinstance(new_value, Mapping):
                    new_value = new_value.get("name")
                text = _text(new_value)
                if text:
                    return text

    return None


def _extract_issue_id(context: Mapping[str, Any]) -> str | None:
    for key in ("issueId", "issue_id", "id", "identifier", "key"):
        value = _text(context.get(key))
        if value:
            return value
    return None


def _extract_title(context: Mapping[str, Any]) -> str | None:
    for key in ("title", "name"):
        value = _text(context.get(key))
        if value:
            return value
    return None


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def _normalize_status(value: Any) -> str:
    text = _text(value)
    if not text:
        return ""
    return re.sub(r"[\s_-]+", " ", _split_camel_case(text)).strip().lower()


def _normalize_event_value(value: Any) -> str:
    text = _text(value)
    if not text:
        return ""
    return re.sub(r"[^a-z0-9]+", "", _split_camel_case(text).lower())


def _normalize_field_name(value: Any) -> str:
    text = _text(value)
    if not text:
        return ""
    return re.sub(r"[^a-z0-9_]+", "", _split_camel_case(text).lower())


def _split_camel_case(value: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _text(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
