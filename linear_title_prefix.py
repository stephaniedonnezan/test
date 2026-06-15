"""Build Linear issue title updates for Cursor research automation.

The automation trigger payloads used for this workflow can arrive either as a
flat ``triggerContext`` object or as a nested Linear webhook payload.  This
module keeps the decision local and side-effect free: callers pass a payload and
receive the title update action to apply, or ``None`` when no update is needed.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue enters research."""

    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_change_event(contexts):
        return None

    if _normalize_status(_extract_status(contexts)) != TARGET_STATUS:
        return None

    issue_id = _extract_text(contexts, ("id", "issueId", "issue_id", "identifier", "key"))
    title = _extract_text(contexts, ("title", "issueTitle", "issue_title"))
    if not issue_id or not title:
        return None

    if title.casefold().startswith(PREFIX.casefold()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)

    add(event.get("triggerContext"))

    data = event.get("data")
    if isinstance(data, Mapping):
        add(data.get("issue"))
        add(data)

    add(event.get("issue"))
    add(event)
    return contexts


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    trigger_fields = ("trigger", "webhookType", "action", "type", "event")
    direct_status_events = {
        "status changed",
        "status change",
        "status updated",
        "state changed",
        "workflow state changed",
    }
    issue_update_events = {"update", "updated", "issue updated", "updated issue"}
    has_status_field_update = any(_updated_status_fields(context) for context in contexts)

    for context in contexts:
        for field in trigger_fields:
            normalized = _normalize_words(context.get(field))
            if normalized in direct_status_events:
                return True
            if normalized in issue_update_events and has_status_field_update:
                return True

        if has_status_field_update and (
            _extract_status([context]) is not None or _changed_status_value(context) is not None
        ):
            return True

    return False


def _updated_status_fields(context: Mapping[str, Any]) -> bool:
    field_values = (
        context.get("updatedFields"),
        context.get("changedFields"),
        context.get("changes"),
        context.get("updated_fields"),
        context.get("changed_fields"),
    )

    return any(_contains_status_field(value) for value in field_values)


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(_is_status_field(key) for key in value.keys())
    if isinstance(value, (list, tuple, set)):
        return any(_contains_status_field(item) for item in value)
    return _is_status_field(value)


def _is_status_field(value: Any) -> bool:
    normalized = _normalize_words(value)
    return normalized in {"status", "state", "workflow state"}


def _extract_status(contexts: list[Mapping[str, Any]]) -> Any:
    explicit_keys = (
        "newStatus",
        "new_status",
        "statusName",
        "status_name",
        "stateName",
        "state_name",
        "workflowStateName",
        "workflow_state_name",
    )
    fallback_keys = ("status", "state", "workflowState", "workflow_state")

    for context in contexts:
        changed_status = _changed_status_value(context)
        if changed_status is not None:
            return changed_status

        for key in explicit_keys:
            if key in context:
                return _status_value(context[key])

    for context in contexts:
        for key in fallback_keys:
            if key in context:
                return _status_value(context[key])

    return None


def _changed_status_value(context: Mapping[str, Any]) -> Any:
    for key in ("changes", "updatedFields", "changedFields", "updated_fields", "changed_fields"):
        value = context.get(key)
        found = _changed_status_value_from(value)
        if found is not None:
            return found
    return None


def _changed_status_value_from(value: Any) -> Any:
    if isinstance(value, Mapping):
        for key, change in value.items():
            if _is_status_field(key):
                return _new_change_value(change)
        for change in value.values():
            found = _changed_status_value_from(change)
            if found is not None:
                return found
    elif isinstance(value, (list, tuple)):
        for item in value:
            if isinstance(item, Mapping):
                field_name = item.get("field") or item.get("name") or item.get("key")
                if _is_status_field(field_name):
                    return _new_change_value(item)
                found = _changed_status_value_from(item)
                if found is not None:
                    return found
            elif _is_status_field(item):
                return None
    return None


def _new_change_value(change: Any) -> Any:
    if isinstance(change, Mapping):
        for key in ("to", "new", "newValue", "new_value", "after", "value"):
            if key in change:
                return _status_value(change[key])
    return _status_value(change)


def _status_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        for key in ("name", "title", "status", "state", "value"):
            if key in value:
                return _status_value(value[key])
        return None
    return value


def _extract_text(contexts: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _normalize_status(value: Any) -> str:
    return _normalize_words(_status_value(value))


def _normalize_words(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    value = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    value = re.sub(r"[^A-Za-z0-9]+", " ", value)
    return " ".join(value.casefold().split())


def main() -> int:
    payload = json.load(sys.stdin)
    action = build_issue_title_update(payload)
    print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
