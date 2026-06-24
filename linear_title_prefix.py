"""Build title update actions for Linear issues moved to research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow state"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title-update action when a Linear issue enters To Research."""
    if not isinstance(event, Mapping):
        return None

    issue_context = _issue_context(event)
    if issue_context is None:
        return None

    if not _is_status_change_event(event):
        return None

    new_status = _new_status(event)
    if _normalize_text(new_status) != TARGET_STATUS:
        return None

    issue_id = _first_string(issue_context, ("issueId", "issue_id", "id", "identifier", "key"))
    title = _first_string(issue_context, ("title", "name", "summary"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_research_prefix(title):
        updated_title = title
    else:
        updated_title = f"{PREFIX}: {title}"

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": updated_title,
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    contexts = list(_event_contexts(event))
    trigger_values = []
    for context in contexts:
        trigger_values.extend(
            _string_values(context, ("trigger", "webhookType", "webhook_type", "action", "type"))
        )

    if any(_is_direct_status_change(value) for value in trigger_values):
        return True

    is_update_event = any(_normalize_text(value) in {"update", "updated", "issue updated", "updated issue"} for value in trigger_values)
    return is_update_event and any(_has_status_change_metadata(context) for context in contexts)


def _new_status(event: Mapping[str, Any]) -> str | None:
    for context in _event_contexts(event):
        value = _first_status_string(
            context,
            (
                "newStatus",
                "new_status",
                "toStatus",
                "to_status",
                "statusName",
                "status_name",
                "newState",
                "new_state",
            ),
        )
        if value:
            return value

    for context in _event_contexts(event):
        value = _status_from_changes(context)
        if value:
            return value

    issue_context = _issue_context(event)
    if issue_context is not None:
        return _first_status_string(issue_context, ("status", "state", "workflowState", "workflow_state"))

    return None


def _issue_context(event: Mapping[str, Any]) -> Mapping[str, Any] | None:
    candidates: list[Mapping[str, Any]] = []

    trigger_context = _mapping_value(event, "triggerContext")
    if trigger_context is not None:
        candidates.extend(_nested_issue_contexts(trigger_context))
        candidates.append(trigger_context)

    data = _mapping_value(event, "data")
    if data is not None:
        candidates.extend(_nested_issue_contexts(data))
        candidates.append(data)

    candidates.extend(_nested_issue_contexts(event))
    candidates.append(event)

    for candidate in candidates:
        if _first_string(candidate, ("title", "name", "summary")) and _first_string(
            candidate, ("issueId", "issue_id", "id", "identifier", "key")
        ):
            return candidate
    return None


def _nested_issue_contexts(context: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    nested = []
    for key in ("issue", "node"):
        value = _mapping_value(context, key)
        if value is not None:
            nested.append(value)

    data = _mapping_value(context, "data")
    if data is not None:
        issue = _mapping_value(data, "issue")
        if issue is not None:
            nested.append(issue)
        nested.append(data)

    return nested


def _event_contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    seen: set[int] = set()
    stack = [event]
    for key in ("triggerContext", "data", "issue"):
        value = _mapping_value(event, key)
        if value is not None:
            stack.append(value)

    while stack:
        context = stack.pop(0)
        context_id = id(context)
        if context_id in seen:
            continue
        seen.add(context_id)
        yield context
        for value in context.values():
            if isinstance(value, Mapping):
                stack.append(value)


def _has_status_change_metadata(context: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        value = context.get(key)
        if isinstance(value, str) and _is_status_field(value):
            return True
        if isinstance(value, Iterable) and not isinstance(value, (str, bytes, Mapping)):
            if any(_is_status_field(item) for item in value):
                return True

    changes = context.get("changes") or context.get("updatedFrom") or context.get("updated_from")
    if isinstance(changes, Mapping):
        return any(_is_status_field(key) for key in changes)

    return False


def _status_from_changes(context: Mapping[str, Any]) -> str | None:
    changes = context.get("changes") or context.get("updatedFrom") or context.get("updated_from")
    if not isinstance(changes, Mapping):
        return None

    for key, value in changes.items():
        if not _is_status_field(key):
            continue
        if isinstance(value, Mapping):
            new_value = value.get("new") or value.get("to") or value.get("after")
            if new_value is not None:
                return _status_value(new_value)
        return _status_value(value)

    return None


def _first_string(context: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for key in keys:
        value = context.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _first_status_string(context: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for key in keys:
        if key in context:
            value = _status_value(context[key])
            if value:
                return value
    return None


def _status_value(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value
    if isinstance(value, Mapping):
        return _first_string(value, ("name", "title", "status", "state"))
    return None


def _string_values(context: Mapping[str, Any], keys: Iterable[str]) -> list[str]:
    values = []
    for key in keys:
        value = context.get(key)
        if isinstance(value, str) and value.strip():
            values.append(value)
    return values


def _mapping_value(context: Mapping[str, Any], key: str) -> Mapping[str, Any] | None:
    value = context.get(key)
    if isinstance(value, Mapping):
        return value
    return None


def _is_direct_status_change(value: str) -> bool:
    normalized = _normalize_text(value)
    return normalized in {"status changed", "status change", "state changed", "state change", "workflow state changed"}


def _is_status_field(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    return _normalize_text(value) in STATUS_FIELD_NAMES


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def _normalize_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
