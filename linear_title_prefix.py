"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "workflowstate"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue-title update action when an issue enters To Research.

    The handler accepts both Cursor Automation trigger contexts and common
    Linear webhook shapes. Non-status-change events, non-target statuses,
    missing issue identifiers/titles, and already-prefixed titles return None.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_change_event(contexts):
        return None

    if not any(_is_target_status(value) for value in _new_status_values(contexts)):
        return None

    issue_id = _first_text(contexts, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_text(contexts, ("title", "name"))
    if issue_id is None or title is None:
        return None

    clean_title = title.strip()
    if not clean_title or _already_prefixed(clean_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {clean_title}",
    }


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return likely event/issue mappings ordered by metadata priority."""

    contexts: list[Mapping[str, Any]] = [event]

    trigger_context = _mapping_at(event, "triggerContext")
    if trigger_context is not None:
        contexts.append(trigger_context)

    data = _mapping_at(event, "data")
    if data is not None:
        contexts.append(data)
        issue = _mapping_at(data, "issue")
        if issue is not None:
            contexts.append(issue)

    issue = _mapping_at(event, "issue")
    if issue is not None:
        contexts.append(issue)

    # Keep first occurrences so outer trigger metadata wins over nested issue
    # objects, which often carry generic values such as type="Issue".
    deduped: list[Mapping[str, Any]] = []
    seen: set[int] = set()
    for context in contexts:
        context_id = id(context)
        if context_id not in seen:
            deduped.append(context)
            seen.add(context_id)
    return deduped


def _is_status_change_event(contexts: Sequence[Mapping[str, Any]]) -> bool:
    trigger_values = [
        _normalize_words(value)
        for context in contexts
        for key in ("trigger", "webhookType", "action", "type", "eventType")
        if (value := context.get(key)) is not None
    ]

    if any(_is_direct_status_change(value) for value in trigger_values):
        return True

    is_update_event = any(value in {"update", "updated", "issue update", "issue updated", "updated issue"} for value in trigger_values)
    return is_update_event and any(_has_status_change_details(context) for context in contexts)


def _is_direct_status_change(value: str) -> bool:
    return (
        "status change" in value
        or "state change" in value
        or "workflow state change" in value
        or value in {"status changed", "state changed", "workflow state changed"}
    )


def _has_status_change_details(context: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        if _contains_status_field(context.get(key)):
            return True

    for key in ("changes", "changed", "previousValues", "previous_values"):
        if _changes_include_status(context.get(key)):
            return True

    return False


def _new_status_values(contexts: Sequence[Mapping[str, Any]]) -> list[Any]:
    explicit_keys = (
        "newStatus",
        "new_status",
        "toStatus",
        "to_status",
        "statusName",
        "status_name",
        "stateName",
        "state_name",
        "workflowStateName",
        "workflow_state_name",
    )
    fallback_keys = ("status", "state", "workflowState", "workflow_state")

    values: list[Any] = []
    for key_group in (explicit_keys, fallback_keys):
        for context in contexts:
            for key in key_group:
                if key in context:
                    values.append(context[key])

    for context in contexts:
        for key in ("changes", "changed"):
            values.extend(_new_status_values_from_changes(context.get(key)))

    return values


def _new_status_values_from_changes(value: Any) -> list[Any]:
    values: list[Any] = []
    if isinstance(value, Mapping):
        for key, change in value.items():
            if _is_status_field_name(str(key)):
                extracted = _extract_new_value(change)
                if extracted is not None:
                    values.append(extracted)
            values.extend(_new_status_values_from_changes(change))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for item in value:
            values.extend(_new_status_values_from_changes(item))
    return values


def _extract_new_value(value: Any) -> Any:
    if not isinstance(value, Mapping):
        return value

    for key in ("newValue", "new_value", "to", "after", "new", "current", "name", "title"):
        if key in value:
            candidate = value[key]
            if isinstance(candidate, Mapping):
                nested = _extract_new_value(candidate)
                if nested is not None:
                    return nested
            else:
                return candidate
    return None


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field_name(value)
    if isinstance(value, Mapping):
        return any(_is_status_field_name(str(key)) or _contains_status_field(item) for key, item in value.items())
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return any(_contains_status_field(item) for item in value)
    return False


def _changes_include_status(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(_is_status_field_name(str(key)) or _changes_include_status(item) for key, item in value.items())
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return any(_changes_include_status(item) for item in value)
    return False


def _is_status_field_name(value: str) -> bool:
    return _normalize_field_name(value) in STATUS_FIELD_NAMES


def _is_target_status(value: Any) -> bool:
    return _normalize_words(_status_text(value)) == TARGET_STATUS


def _status_text(value: Any) -> str:
    if isinstance(value, Mapping):
        for key in ("name", "title", "label", "status", "state", "workflowState"):
            if key in value:
                return _status_text(value[key])
        return ""
    return str(value)


def _first_text(contexts: Sequence[Mapping[str, Any]], keys: Sequence[str]) -> str | None:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _already_prefixed(title: str) -> bool:
    return title.casefold().startswith(TITLE_PREFIX.casefold())


def _mapping_at(mapping: Mapping[str, Any], key: str) -> Mapping[str, Any] | None:
    value = mapping.get(key)
    return value if isinstance(value, Mapping) else None


def _normalize_words(value: Any) -> str:
    text = _split_camel_case(str(value))
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().casefold()


def _normalize_field_name(value: str) -> str:
    return _normalize_words(value).replace(" ", "")


def _split_camel_case(value: str) -> str:
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    return re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", value)


def main() -> int:
    payload = json.load(sys.stdin)
    update = build_issue_title_update(payload)
    print(json.dumps(update, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
