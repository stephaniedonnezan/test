"""Build Linear issue title updates for research status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title-update action when an issue moves to "to research"."""
    if not isinstance(event, Mapping):
        return None

    contexts = _payload_contexts(event)
    if not contexts:
        return None

    if not _is_status_change_event(contexts):
        return None

    status = _new_status(contexts)
    if _normalize_token(status) != _normalize_token(TARGET_STATUS):
        return None

    issue_id = _issue_id(contexts)
    title = _issue_title(contexts)
    if not issue_id or not title:
        return None

    if _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _payload_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)

    add(event)
    add(event.get("triggerContext"))
    data = event.get("data")
    add(data)

    if isinstance(data, Mapping):
        add(data.get("issue"))
        add(data.get("state"))
        add(data.get("workflowState"))

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        add(trigger_context.get("issue"))
        add(trigger_context.get("state"))
        add(trigger_context.get("workflowState"))

    return contexts


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    trigger_tokens: list[str] = []
    update_seen = False

    for context in contexts:
        for key in ("trigger", "webhookType", "action", "type"):
            value = context.get(key)
            normalized = _normalize_token(value)
            if not normalized:
                continue
            trigger_tokens.append(normalized)
            if normalized in {"update", "issueupdate", "issueupdated", "updatedissue"}:
                update_seen = True

        if _changed_status_fields(context):
            return True

    if any(token in {"statuschanged", "statechanged", "workflowstatechanged"} for token in trigger_tokens):
        return True

    if update_seen:
        return any(_changed_status_fields(context) for context in contexts)

    return False


def _changed_status_fields(context: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "changedFields"):
        fields = context.get(key)
        if _contains_status_field(fields):
            return True

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        if any(_normalize_token(key) in STATUS_FIELDS for key in changes):
            return True
    elif _contains_status_field(changes):
        return True

    return False


def _contains_status_field(fields: Any) -> bool:
    if isinstance(fields, str):
        return _normalize_token(fields) in STATUS_FIELDS

    if isinstance(fields, Mapping):
        return any(_normalize_token(key) in STATUS_FIELDS for key in fields)

    if isinstance(fields, Iterable):
        return any(_normalize_token(field) in STATUS_FIELDS for field in fields)

    return False


def _new_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        value = _first_string(
            context,
            (
                "newStatus",
                "new_status",
                "statusName",
                "stateName",
                "workflowStateName",
                "workflow_state_name",
            ),
        )
        if value:
            return value

        changes = context.get("changes")
        changed_value = _status_from_changes(changes)
        if changed_value:
            return changed_value

    for context in contexts:
        value = _status_from_context(context)
        if value:
            return value

    return None


def _status_from_changes(changes: Any) -> str | None:
    if not isinstance(changes, Mapping):
        return None

    for key in ("status", "state", "workflowState", "workflow_state"):
        change = changes.get(key)
        if not isinstance(change, Mapping):
            continue

        for value_key in ("newValue", "new_value", "to", "after", "name"):
            value = change.get(value_key)
            if isinstance(value, str) and value.strip():
                return value.strip()
            if isinstance(value, Mapping):
                name = _first_string(value, ("name", "status", "title"))
                if name:
                    return name

    return None


def _status_from_context(context: Mapping[str, Any]) -> str | None:
    status = context.get("status")
    if isinstance(status, str) and status.strip():
        return status.strip()
    if isinstance(status, Mapping):
        value = _first_string(status, ("name", "title"))
        if value:
            return value

    for key in ("state", "workflowState", "workflow_state"):
        value = context.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, Mapping):
            name = _first_string(value, ("name", "title"))
            if name:
                return name

    return None


def _issue_id(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        value = _first_string(context, ("identifier", "issueId", "issue_id", "key"))
        if value:
            return value

    for context in contexts:
        value = _first_string(context, ("id",))
        if value:
            return value

    return None


def _issue_title(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        value = _first_string(context, ("title", "name"))
        if value:
            return value

    return None


def _first_string(context: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for key in keys:
        value = context.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def _normalize_token(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return re.sub(r"[^a-z0-9]+", "", spaced.lower())


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
