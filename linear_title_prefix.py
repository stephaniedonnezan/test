"""Build Linear issue title updates for Cursor research handoffs."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "workflowstate"}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update action when an issue enters To Research."""
    if not isinstance(event, Mapping):
        return None

    contexts = list(_candidate_mappings(event))
    if not _is_status_change(contexts):
        return None

    if _normalize_text(_new_status(contexts)) != TARGET_STATUS:
        return None

    issue_id = _clean_string(_first_value(contexts, ("issueId", "issue_id", "id", "identifier", "key")))
    title = _clean_string(_first_value(contexts, ("title", "name")))
    if issue_id is None or title is None:
        return None

    if title.lower().startswith(TITLE_PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _candidate_mappings(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    candidates: list[Mapping[str, Any]] = []
    seen: set[int] = set()

    def add(value: Any) -> None:
        if not isinstance(value, Mapping) or id(value) in seen:
            return
        seen.add(id(value))
        candidates.append(value)

    add(event)
    for key in ("automation_trigger_info", "automationTriggerInfo"):
        add(event.get(key))

    # Issue-like records are preferred for id/title extraction, while outer
    # webhook records still remain available for trigger metadata.
    prioritized_nested_keys = ("triggerContext", "trigger_context", "issue", "node", "data")
    index = 0
    while index < len(candidates):
        current = candidates[index]
        for key in prioritized_nested_keys:
            add(current.get(key))
        index += 1

    issue_like = [
        item
        for item in candidates
        if any(_clean_string(item.get(key)) for key in ("issueId", "issue_id", "id", "identifier", "key"))
        and any(_clean_string(item.get(key)) for key in ("title", "name"))
    ]
    metadata_like = [item for item in candidates if item not in issue_like]
    return issue_like + metadata_like


def _is_status_change(contexts: list[Mapping[str, Any]]) -> bool:
    trigger_values = (
        "trigger",
        "triggerType",
        "trigger_type",
        "webhookType",
        "webhook_type",
        "action",
        "type",
    )
    normalized_triggers = {
        _normalize_text(value)
        for context in contexts
        for value in (context.get(key) for key in trigger_values)
        if value is not None
    }

    if normalized_triggers & {"status changed", "status change", "state changed", "workflow state changed"}:
        return True

    generic_update = bool(
        normalized_triggers
        & {"update", "updated", "issue update", "issue updated", "updated issue"}
    )
    return generic_update and _mentions_status_field(contexts)


def _mentions_status_field(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        fields = context.get("updatedFields") or context.get("updated_fields") or context.get("changedFields")
        if _contains_status_field(fields):
            return True

        changes = context.get("changes") or context.get("changed") or context.get("updatedFrom")
        if isinstance(changes, Mapping):
            if any(_status_field_name(key) for key in changes):
                return True
        elif _contains_status_field(changes):
            return True
    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _status_field_name(value)
    if isinstance(value, Mapping):
        return any(_status_field_name(key) for key in value)
    if isinstance(value, list | tuple | set):
        return any(_contains_status_field(item) for item in value)
    return False


def _status_field_name(value: Any) -> bool:
    return _normalize_key(value) in STATUS_FIELD_NAMES


def _new_status(contexts: list[Mapping[str, Any]]) -> Any:
    explicit_keys = (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "toStatus",
        "to_status",
        "targetStatus",
        "target_status",
    )
    value = _first_value(contexts, explicit_keys)
    if value is not None:
        return value

    for context in contexts:
        changes = context.get("changes") or context.get("changed")
        if not isinstance(changes, Mapping):
            continue
        for field, change in changes.items():
            if _status_field_name(field):
                value = _change_new_value(change)
                if value is not None:
                    return value

    return _first_value(contexts, ("status", "state", "workflowState", "workflow_state"))


def _change_new_value(change: Any) -> Any:
    if not isinstance(change, Mapping):
        return change
    for key in ("to", "new", "after", "toValue", "to_value", "value", "name"):
        value = change.get(key)
        if value is not None:
            return value
    return None


def _first_value(contexts: list[Mapping[str, Any]], keys: tuple[str, ...]) -> Any:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if value is not None:
                return _named_value(value)
    return None


def _named_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            nested = value.get(key)
            if nested is not None:
                return nested
        return None
    return value


def _clean_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def _normalize_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", _normalize_text(value))


def _normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    normalized = re.sub(r"[^A-Za-z0-9]+", " ", spaced).strip().lower()
    return re.sub(r"\s+", " ", normalized)


def main() -> int:
    event = json.load(sys.stdin)
    result = build_issue_title_update(event)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
