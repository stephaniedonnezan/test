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


def build_issue_title_update(event: Any) -> dict[str, str] | None:
    """Return a title-update action when a Linear issue moves to To Research."""

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    if _normalize(_new_status(event)) != TARGET_STATUS:
        return None

    contexts = _issue_contexts(event)
    issue_id = _first_text(contexts, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_text(contexts, ("title", "name"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if not title or title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    event_names = [
        _normalize(value)
        for context in _event_contexts(event)
        for key in ("trigger", "webhookType", "webhook_type", "action", "type")
        for value in [_get(context, key)]
        if value is not None
    ]

    if any(name in {"status changed", "status change"} for name in event_names):
        return True

    is_update_event = any(
        name in {"update", "updated", "issue update", "issue updated", "updated issue"}
        for name in event_names
    )
    return is_update_event and _has_status_field_change(event)


def _has_status_field_change(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized_key = _normalize_key(key)
            if normalized_key in {
                "updatedfields",
                "updated_fields",
                "changedfields",
                "changed_fields",
            }:
                if _field_list_mentions_status(item):
                    return True

            if normalized_key in {"changes", "changed", "updatedfrom", "updated_from"}:
                if _change_map_mentions_status(item):
                    return True

            if _has_status_field_change(item):
                return True

    if isinstance(value, list):
        return any(_has_status_field_change(item) for item in value)

    return False


def _field_list_mentions_status(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_key(value) in STATUS_FIELDS

    if isinstance(value, Mapping):
        return any(_field_list_mentions_status(item) for item in value.values())

    if isinstance(value, Iterable):
        return any(_field_list_mentions_status(item) for item in value)

    return False


def _change_map_mentions_status(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(
            _normalize_key(key) in STATUS_FIELDS or _change_map_mentions_status(item)
            for key, item in value.items()
        )

    if isinstance(value, list):
        return any(_change_map_mentions_status(item) for item in value)

    return False


def _new_status(event: Mapping[str, Any]) -> str | None:
    explicit_keys = (
        "newStatus",
        "new_status",
        "newStatusName",
        "new_status_name",
        "statusName",
        "status_name",
        "newState",
        "new_state",
        "newWorkflowState",
        "new_workflow_state",
    )
    fallback_keys = ("status", "state", "workflowState", "workflow_state")

    contexts = _event_contexts(event)
    return (
        _first_status_value(contexts, explicit_keys)
        or _status_from_changes(event)
        or _first_status_value(contexts, fallback_keys)
    )


def _status_from_changes(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized_key = _normalize_key(key)
            if normalized_key in STATUS_FIELDS:
                status = _status_value(item)
                if status:
                    return status

            if normalized_key in {"changes", "changed"}:
                status = _changed_status_value(item)
                if status:
                    return status

            status = _status_from_changes(item)
            if status:
                return status

    if isinstance(value, list):
        for item in value:
            status = _status_from_changes(item)
            if status:
                return status

    return None


def _changed_status_value(value: Any) -> str | None:
    if not isinstance(value, Mapping):
        return None

    for key, item in value.items():
        if _normalize_key(key) not in STATUS_FIELDS:
            continue

        if isinstance(item, Mapping):
            for target_key in ("to", "after", "new", "newValue", "new_value", "name"):
                status = _status_value(_get(item, target_key))
                if status:
                    return status
        else:
            status = _status_value(item)
            if status:
                return status

    return None


def _first_status_value(
    contexts: list[Mapping[str, Any]], keys: tuple[str, ...]
) -> str | None:
    for context in contexts:
        for key in keys:
            status = _status_value(_get(context, key))
            if status:
                return status
    return None


def _status_value(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            status = _status_value(_get(value, key))
            if status:
                return status

    return None


def _event_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = [event]

    for key in ("triggerContext", "trigger_context", "data", "issue"):
        nested = _get(event, key)
        if isinstance(nested, Mapping):
            contexts.append(nested)
            if key == "data":
                issue = _get(nested, "issue")
                if isinstance(issue, Mapping):
                    contexts.append(issue)

    return contexts


def _issue_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []

    for key in ("triggerContext", "trigger_context"):
        nested = _get(event, key)
        if isinstance(nested, Mapping):
            contexts.append(nested)

    data = _get(event, "data")
    if isinstance(data, Mapping):
        issue = _get(data, "issue")
        if isinstance(issue, Mapping):
            contexts.append(issue)
        contexts.append(data)

    issue = _get(event, "issue")
    if isinstance(issue, Mapping):
        contexts.append(issue)

    contexts.append(event)
    return contexts


def _first_text(contexts: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for context in contexts:
        for key in keys:
            value = _get(context, key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _get(mapping: Mapping[str, Any], name: str) -> Any:
    if name in mapping:
        return mapping[name]

    normalized_name = _normalize_key(name)
    for key, value in mapping.items():
        if _normalize_key(key) == normalized_name:
            return value

    return None


def _normalize(value: Any) -> str:
    if value is None:
        return ""

    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", str(value))
    text = re.sub(r"[_\-\s]+", " ", text)
    return text.strip().lower()


def _normalize_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9_]", "", _normalize(value).replace(" ", "_"))


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        print("null")
        return 0

    print(json.dumps(build_issue_title_update(event)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
