"""Build Linear issue title updates for issues moved to research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_UPDATE_FIELDS = {
    "status",
    "state",
    "workflowstate",
    "workflowstatus",
    "workflow_state",
    "workflow_status",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear issue title update action when the event enters research."""

    if not isinstance(event, Mapping):
        return None

    contexts = _candidate_contexts(event)
    if not contexts:
        return None

    merged = _merge_contexts(contexts)
    if not _is_status_change_event(contexts):
        return None

    new_status = _extract_new_status(contexts, merged)
    if _normalize_text(new_status) != TARGET_STATUS:
        return None

    issue_id = _first_string(
        merged,
        ("issueId", "issue_id", "id", "identifier", "key"),
    )
    title = _first_string(merged, ("title", "name"))
    if issue_id is None or title is None:
        return None

    clean_title = title.strip()
    if not clean_title:
        return None

    if _has_title_prefix(clean_title):
        prefixed_title = clean_title
    else:
        prefixed_title = f"{TITLE_PREFIX}: {clean_title}"

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": prefixed_title,
    }


def _candidate_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping):
            contexts.append(value)

    add(event)
    for key in ("triggerContext", "data"):
        add(event.get(key))

    data = event.get("data")
    if isinstance(data, Mapping):
        for key in ("issue", "node"):
            add(data.get(key))

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        for key in ("data", "issue"):
            add(trigger_context.get(key))

    return contexts


def _merge_contexts(contexts: list[Mapping[str, Any]]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    # Later contexts usually contain the specific issue fields, while outer
    # contexts contain trigger metadata. Preserve both with outer fields winning.
    for context in reversed(contexts):
        merged.update(context)
    return merged


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    event_names: list[str] = []
    for context in contexts:
        for key in ("trigger", "webhookType", "action", "type"):
            value = context.get(key)
            if isinstance(value, str):
                event_names.append(_normalize_text(value))

    if any(name in {"status changed", "status change"} for name in event_names):
        return True

    if any(name in {"update", "updated", "issue updated", "updated issue"} for name in event_names):
        return any(_context_mentions_status_field(context) for context in contexts)

    return False


def _context_mentions_status_field(context: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        if _contains_status_field(context.get(key)):
            return True

    for key in ("changes", "changed"):
        changes = context.get(key)
        if isinstance(changes, Mapping):
            if any(_is_status_field(field) for field in changes):
                return True
        elif _contains_status_field(changes):
            return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)
    if isinstance(value, Mapping):
        return any(_is_status_field(key) for key in value)
    if isinstance(value, list | tuple | set):
        return any(_contains_status_field(item) for item in value)
    return False


def _is_status_field(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    return _normalize_key(value) in {_normalize_key(field) for field in STATUS_UPDATE_FIELDS}


def _extract_new_status(contexts: list[Mapping[str, Any]], merged: Mapping[str, Any]) -> str | None:
    explicit_keys = (
        "newStatus",
        "new_status",
        "statusName",
        "status_name",
        "newState",
        "new_state",
        "newWorkflowState",
        "new_workflow_state",
    )
    for context in contexts:
        status = _first_status_value(context, explicit_keys)
        if status is not None:
            return status

    for context in contexts:
        changes_status = _status_from_changes(context)
        if changes_status is not None:
            return changes_status

    return _first_status_value(merged, ("status", "state", "workflowState", "workflow_status"))


def _status_from_changes(context: Mapping[str, Any]) -> str | None:
    changes = context.get("changes")
    if not isinstance(changes, Mapping):
        changes = context.get("changed")
    if not isinstance(changes, Mapping):
        return None

    for key, value in changes.items():
        if not _is_status_field(key):
            continue
        if isinstance(value, Mapping):
            for nested_key in ("newValue", "new_value", "to", "after", "name"):
                status = _string_or_name(value.get(nested_key))
                if status is not None:
                    return status
        else:
            status = _string_or_name(value)
            if status is not None:
                return status
    return None


def _first_status_value(context: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        status = _string_or_name(context.get(key))
        if status is not None:
            return status
    return None


def _first_string(context: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = context.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _string_or_name(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            nested = value.get(key)
            if isinstance(nested, str) and nested.strip():
                return nested
    return None


def _has_title_prefix(title: str) -> bool:
    return title.casefold().startswith(TITLE_PREFIX.casefold())


def _normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    with_spaces = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    with_spaces = re.sub(r"[_-]+", " ", with_spaces)
    return re.sub(r"\s+", " ", with_spaces).strip().casefold()


def _normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", _normalize_text(value))


def main() -> int:
    """Read a JSON event from stdin and print the title update action."""

    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
