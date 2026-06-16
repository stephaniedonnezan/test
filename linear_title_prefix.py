"""Build Linear issue-title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflowstatus"}
STATUS_TRIGGER_NAMES = {"statuschanged", "statuschange", "statusupdated", "statusupdate"}
GENERIC_UPDATE_NAMES = {
    "issueupdated",
    "updatedissue",
    "update",
    "updated",
    "issueupdate",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear issue title update action when a research status change occurs."""
    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_change_event(contexts):
        return None

    status = _find_status(contexts)
    if _normalize_text(status) != TARGET_STATUS:
        return None

    issue_id = _find_first_string(contexts, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _find_first_string(contexts, ("title", "name"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if not title or _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []

    def visit(value: Any) -> None:
        if not isinstance(value, Mapping):
            return
        contexts.append(value)
        for key in ("triggerContext", "webhook", "payload", "data", "issue", "node"):
            nested = value.get(key)
            if isinstance(nested, Mapping):
                visit(nested)

    visit(event)
    return contexts


def _is_status_change_event(contexts: Sequence[Mapping[str, Any]]) -> bool:
    names: list[str] = []
    for context in contexts:
        for key in ("trigger", "event", "action", "type", "webhookType"):
            value = context.get(key)
            if isinstance(value, str):
                names.append(_compact_text(value))

    if any(name in STATUS_TRIGGER_NAMES for name in names):
        return True

    if any(name in GENERIC_UPDATE_NAMES for name in names):
        return _mentions_status_field(contexts)

    return _mentions_status_field(contexts) and _find_status(contexts) is not None


def _mentions_status_field(contexts: Sequence[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "changedFields", "changes", "updated_fields"):
            value = context.get(key)
            if _value_mentions_status(value):
                return True
    return False


def _value_mentions_status(value: Any) -> bool:
    if isinstance(value, str):
        return _field_name_is_status(value)
    if isinstance(value, Mapping):
        return any(_field_name_is_status(key) or _value_mentions_status(item) for key, item in value.items())
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return any(_value_mentions_status(item) for item in value)
    return False


def _field_name_is_status(value: Any) -> bool:
    return isinstance(value, str) and _compact_text(value) in STATUS_FIELD_NAMES


def _find_status(contexts: Sequence[Mapping[str, Any]]) -> str | None:
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
    status = _find_first_string(contexts, explicit_keys)
    if status:
        return status

    for context in contexts:
        for key in ("status", "state", "workflowState", "workflow_status"):
            value = context.get(key)
            status = _string_from_status_value(value)
            if status:
                return status

    return None


def _string_from_status_value(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        return _first_string_in_mapping(value, ("name", "title", "status", "state"))
    return None


def _find_first_string(contexts: Sequence[Mapping[str, Any]], keys: Sequence[str]) -> str | None:
    for context in contexts:
        value = _first_string_in_mapping(context, keys)
        if value:
            return value
    return None


def _first_string_in_mapping(mapping: Mapping[str, Any], keys: Sequence[str]) -> str | None:
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _has_prefix(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = _split_camel_case(value)
    normalized = re.sub(r"[_\-\s]+", " ", normalized).strip().casefold()
    return normalized or None


def _compact_text(value: str) -> str:
    normalized = _split_camel_case(value)
    return re.sub(r"[^a-z0-9]", "", normalized.casefold())


def _split_camel_case(value: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)


def main() -> int:
    """Read a JSON event from stdin and print the computed action as JSON."""
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    result = build_issue_title_update(event)
    if result is not None:
        print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
