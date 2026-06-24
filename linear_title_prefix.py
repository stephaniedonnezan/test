"""Build Linear issue title updates for Cursor research status automation.

The automation runner can pass either the flat Cursor trigger context or a
Linear-style webhook payload. This module keeps the decision pure so callers can
apply the returned action with their preferred Linear client.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


RESEARCH_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}
STATUS_EVENT_VALUES = {
    "statuschanged",
    "statuschange",
    "statechanged",
    "statechange",
    "workflowstatechanged",
    "workflowstatechange",
}
ISSUE_UPDATE_VALUES = {
    "issueupdated",
    "updatedissue",
    "update",
    "updated",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue enters To Research."""

    if not isinstance(event, Mapping):
        return None

    context = _event_context(event)
    if not _is_status_change_event(context):
        return None

    status = _extract_new_status(context)
    if _normalize_text(status) != _normalize_text(TARGET_STATUS):
        return None

    issue_id = _extract_first_text(context, ("issueId", "issue_id", "id", "identifier", "key"))
    title = _extract_first_text(context, ("title", "name"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_research_prefix(title):
        updated_title = title
    else:
        updated_title = f"{RESEARCH_PREFIX}: {title}"

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": updated_title,
    }


def _event_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge likely Linear/Cursor event containers, preserving outer metadata."""

    context: dict[str, Any] = {}
    for container in _iter_mappings(event):
        context.update(container)

    issue = _find_issue_mapping(event)
    if issue is not None:
        issue_id = _extract_first_text(issue, ("issueId", "issue_id", "id", "identifier", "key"))
        title = _extract_first_text(issue, ("title", "name"))
        if issue_id:
            context["issueId"] = issue_id
        if title:
            context["title"] = title
    return context


def _iter_mappings(value: Any) -> list[Mapping[str, Any]]:
    mappings: list[Mapping[str, Any]] = []

    def visit(node: Any) -> None:
        if not isinstance(node, Mapping):
            return

        for key in ("triggerContext", "data", "issue", "node"):
            nested = node.get(key)
            if isinstance(nested, Mapping):
                visit(nested)

        mappings.append(node)

    visit(value)
    return mappings


def _find_issue_mapping(value: Any) -> Mapping[str, Any] | None:
    if not isinstance(value, Mapping):
        return None

    for key in ("issue", "node"):
        nested = value.get(key)
        if isinstance(nested, Mapping):
            return nested

    for key in ("triggerContext", "data"):
        found = _find_issue_mapping(value.get(key))
        if found is not None:
            return found

    return None


def _is_status_change_event(context: Mapping[str, Any]) -> bool:
    event_values = [
        context.get(key)
        for key in ("trigger", "webhookType", "action", "type", "event", "eventType")
    ]
    normalized_values = {_normalize_event_value(value) for value in event_values if value}

    if normalized_values & STATUS_EVENT_VALUES:
        return True

    if normalized_values & ISSUE_UPDATE_VALUES:
        return _updated_fields_include_status(context) or _changes_include_status(context)

    return False


def _updated_fields_include_status(context: Mapping[str, Any]) -> bool:
    fields = context.get("updatedFields") or context.get("updated_fields") or context.get("changedFields")
    return any(_normalize_field_name(field) in STATUS_FIELDS for field in _iter_field_names(fields))


def _changes_include_status(context: Mapping[str, Any]) -> bool:
    changes = context.get("changes") or context.get("changed") or context.get("change")

    if isinstance(changes, Mapping):
        return any(_normalize_field_name(key) in STATUS_FIELDS for key in changes)

    if isinstance(changes, Sequence) and not isinstance(changes, (str, bytes)):
        for change in changes:
            if isinstance(change, Mapping):
                field = (
                    change.get("field")
                    or change.get("fieldName")
                    or change.get("name")
                    or change.get("key")
                )
                if _normalize_field_name(field) in STATUS_FIELDS:
                    return True
            elif _normalize_field_name(change) in STATUS_FIELDS:
                return True

    return False


def _iter_field_names(fields: Any) -> list[Any]:
    if isinstance(fields, Mapping):
        return list(fields.keys())
    if isinstance(fields, Sequence) and not isinstance(fields, (str, bytes)):
        return list(fields)
    if fields is None:
        return []
    return [fields]


def _extract_new_status(context: Mapping[str, Any]) -> str | None:
    for key in ("newStatus", "new_status"):
        value = context.get(key)
        text = _coerce_status(value)
        if text:
            return text

    for key in ("changes", "changed", "change"):
        text = _extract_status_from_changes(context.get(key))
        if text:
            return text

    for key in ("status", "state", "workflowState", "workflow_state"):
        value = context.get(key)
        text = _coerce_status(value)
        if text:
            return text

    return None


def _extract_status_from_changes(changes: Any) -> str | None:
    if isinstance(changes, Mapping):
        for key, value in changes.items():
            if _normalize_field_name(key) in STATUS_FIELDS:
                return _coerce_status_value_change(value)
        return None

    if isinstance(changes, Sequence) and not isinstance(changes, (str, bytes)):
        for change in changes:
            if not isinstance(change, Mapping):
                continue
            field = change.get("field") or change.get("fieldName") or change.get("name") or change.get("key")
            if _normalize_field_name(field) in STATUS_FIELDS:
                return _coerce_status_value_change(change)

    return None


def _coerce_status_value_change(change: Any) -> str | None:
    if isinstance(change, Mapping):
        for key in ("to", "toValue", "newValue", "after", "name"):
            text = _coerce_status(change.get(key))
            if text:
                return text
    return _coerce_status(change)


def _coerce_status(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, Mapping):
        for key in ("name", "title", "value", "label"):
            text = _coerce_status(value.get(key))
            if text:
                return text
    return None


def _extract_first_text(context: Mapping[str, Any], keys: Sequence[str]) -> str | None:
    for key in keys:
        value = context.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(RESEARCH_PREFIX.lower())


def _normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^a-z0-9]+", "", _split_camel_case(value).lower())


def _normalize_event_value(value: Any) -> str:
    return _normalize_text(value)


def _normalize_field_name(value: Any) -> str:
    return _normalize_text(value)


def _split_camel_case(value: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        json.dump(action, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
