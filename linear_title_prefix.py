"""Build Linear issue title updates for research-status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflow state"}
DIRECT_STATUS_TRIGGERS = {"status changed", "status change"}
ISSUE_UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title-update action when a Linear issue moves to research."""
    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    new_status = _extract_new_status(event)
    if _normalize_text(new_status) != TARGET_STATUS:
        return None

    issue_id = _extract_first_string(_issue_contexts(event), _ISSUE_ID_KEYS)
    title = _extract_first_string(_issue_contexts(event), ("title",))
    if issue_id is None or title is None:
        return None

    title = title.strip()
    if not title or title.lower().startswith(TITLE_PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


_ISSUE_ID_KEYS = ("issueId", "issue_id", "id", "identifier", "key")
_NEW_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "newWorkflowState",
    "new_workflow_state",
    "toStatus",
    "to_status",
)
_CURRENT_STATUS_KEYS = ("status", "state", "workflowState", "workflow_state")
_TRIGGER_KEYS = ("trigger", "webhookType", "webhook_type", "action", "type", "eventType")


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    trigger_names = {
        normalized
        for context in _metadata_contexts(event)
        for key in _TRIGGER_KEYS
        for normalized in [_normalize_text(context.get(key))]
        if normalized is not None
    }
    if trigger_names & DIRECT_STATUS_TRIGGERS:
        return True

    if trigger_names & ISSUE_UPDATE_TRIGGERS:
        return _has_status_field_change(event)

    return False


def _extract_new_status(event: Mapping[str, Any]) -> str | None:
    explicit_status = _extract_status_from_keys(_metadata_contexts(event), _NEW_STATUS_KEYS)
    if explicit_status is not None:
        return explicit_status

    changed_status = _extract_status_from_changes(event)
    if changed_status is not None:
        return changed_status

    return _extract_status_from_keys(_metadata_contexts(event), _CURRENT_STATUS_KEYS)


def _extract_status_from_keys(
    contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]
) -> str | None:
    for context in contexts:
        for key in keys:
            status = _status_value_to_string(context.get(key))
            if status is not None:
                return status
    return None


def _extract_status_from_changes(value: Any) -> str | None:
    for mapping in _walk_mappings(value):
        changes = mapping.get("changes")
        if isinstance(changes, Mapping):
            for field, change in changes.items():
                if _is_status_field(field):
                    status = _extract_new_value(change)
                    if status is not None:
                        return status

        updated_fields = mapping.get("updatedFields") or mapping.get("changedFields")
        for field in _iter_collection(updated_fields):
            if isinstance(field, Mapping):
                name = field.get("field") or field.get("name") or field.get("key")
                if _is_status_field(name):
                    status = _extract_new_value(field)
                    if status is not None:
                        return status
            elif _is_status_field(field):
                status = _extract_status_from_keys((mapping,), _CURRENT_STATUS_KEYS)
                if status is not None:
                    return status

    return None


def _extract_new_value(change: Any) -> str | None:
    if not isinstance(change, Mapping):
        return _status_value_to_string(change)

    for key in ("to", "new", "after", "newValue", "new_value", "value"):
        status = _status_value_to_string(change.get(key))
        if status is not None:
            return status

    return _status_value_to_string(change)


def _has_status_field_change(value: Any) -> bool:
    for mapping in _walk_mappings(value):
        changes = mapping.get("changes")
        if isinstance(changes, Mapping) and any(_is_status_field(key) for key in changes):
            return True

        for fields_key in ("updatedFields", "changedFields"):
            fields = mapping.get(fields_key)
            if any(_field_mentions_status(field) for field in _iter_collection(fields)):
                return True

    return False


def _field_mentions_status(field: Any) -> bool:
    if isinstance(field, Mapping):
        return any(
            _is_status_field(field.get(key))
            for key in ("field", "name", "key", "property", "attribute")
        )

    return _is_status_field(field)


def _is_status_field(value: Any) -> bool:
    return _normalize_text(value) in STATUS_FIELDS


def _status_value_to_string(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "status", "state"):
            nested_value = _status_value_to_string(value.get(key))
            if nested_value is not None:
                return nested_value

    return None


def _extract_first_string(
    contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]
) -> str | None:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _issue_contexts(event: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    contexts: list[Mapping[str, Any]] = []
    trigger_context = event.get("triggerContext")
    data = event.get("data")
    top_level_issue = event.get("issue")

    if isinstance(trigger_context, Mapping):
        contexts.append(trigger_context)
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            contexts.append(issue)
    if isinstance(top_level_issue, Mapping):
        contexts.append(top_level_issue)
    if isinstance(data, Mapping):
        contexts.append(data)
    contexts.append(event)

    return tuple(contexts)


def _metadata_contexts(event: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    contexts: list[Mapping[str, Any]] = [event]
    trigger_context = event.get("triggerContext")
    data = event.get("data")
    top_level_issue = event.get("issue")

    if isinstance(trigger_context, Mapping):
        contexts.append(trigger_context)
    if isinstance(data, Mapping):
        contexts.append(data)
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            contexts.append(issue)
    if isinstance(top_level_issue, Mapping):
        contexts.append(top_level_issue)

    return tuple(contexts)


def _walk_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for child in value.values():
            yield from _walk_mappings(child)
    elif isinstance(value, list | tuple):
        for child in value:
            yield from _walk_mappings(child)


def _iter_collection(value: Any) -> Iterable[Any]:
    if isinstance(value, (str, bytes)) or value is None:
        return ()
    if isinstance(value, Iterable):
        return value
    return ()


def _normalize_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    camel_spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    separator_spaced = re.sub(r"[^A-Za-z0-9]+", " ", camel_spaced)
    normalized = " ".join(separator_spaced.lower().split())
    return normalized or None


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
