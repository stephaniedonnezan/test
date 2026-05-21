"""Build title updates for Linear issues moved into research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {
    "status",
    "status id",
    "state",
    "state id",
    "workflow state",
    "workflow state id",
    "workflow status",
    "workflow status id",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return the title update action for a qualifying Linear status event."""
    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    status = _extract_new_status(event)
    if _normalize_text(status) != TARGET_STATUS:
        return None

    issue_id = _extract_issue_text(event, ("issueId", "issue_id", "identifier", "id"))
    title = _extract_issue_text(event, ("title", "issueTitle", "issue_title"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if not title or _has_title_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    event_types = {
        _normalize_text(value)
        for scope in _metadata_scopes(event)
        for key in ("trigger", "webhookType", "webhook_type", "eventType", "event_type", "action", "type")
        for value in (_mapping_get(scope, key),)
        if isinstance(value, str)
    }

    if event_types & {
        "status changed",
        "status change",
        "state changed",
        "state change",
        "workflow state changed",
        "workflow state change",
    }:
        return True

    if event_types & {"update", "updated", "issue updated", "updated issue"}:
        return _updated_fields_include_status(event)

    return False


def _updated_fields_include_status(event: Mapping[str, Any]) -> bool:
    for scope in _metadata_scopes(event):
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            fields = _mapping_get(scope, key)
            if _fields_include_status(fields):
                return True

        for key in ("updatedFrom", "updated_from", "changes", "changed", "previousValues"):
            changed = _mapping_get(scope, key)
            if isinstance(changed, Mapping) and _fields_include_status(changed.keys()):
                return True

    return False


def _fields_include_status(fields: Any) -> bool:
    if isinstance(fields, str):
        candidates: Iterable[Any] = (fields,)
    elif isinstance(fields, Mapping):
        candidates = fields.keys()
    elif isinstance(fields, Iterable):
        candidates = fields
    else:
        return False

    return any(_normalize_text(str(field)) in _STATUS_FIELD_NAMES for field in candidates)


def _extract_new_status(event: Mapping[str, Any]) -> str | None:
    explicit_keys = (
        "newStatus",
        "new_status",
        "toStatus",
        "to_status",
        "newState",
        "new_state",
        "toState",
        "to_state",
    )
    status_keys = ("status", "state", "workflowState", "workflow_state", "workflowStatus", "workflow_status")

    for scope in _metadata_scopes(event):
        status = _first_text_value(scope, explicit_keys)
        if status:
            return status

    for scope in _issue_scopes(event):
        status = _first_text_value(scope, status_keys)
        if status:
            return status

    return None


def _extract_issue_text(event: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for scope in _issue_scopes(event):
        value = _first_text_value(scope, keys)
        if value and value.strip():
            return value
    return None


def _first_text_value(scope: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = _mapping_get(scope, key)
        if isinstance(value, str):
            return value
        if isinstance(value, Mapping):
            nested_name = _mapping_get(value, "name")
            if isinstance(nested_name, str):
                return nested_name
    return None


def _issue_scopes(event: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    trigger_context = _nested_mapping(event, "triggerContext")
    data = _nested_mapping(event, "data")
    event_issue = _nested_mapping(event, "issue")

    scopes = (
        trigger_context,
        _nested_mapping(trigger_context, "issue"),
        _nested_mapping(data, "issue"),
        event_issue,
        data,
        event,
    )
    return tuple(scope for scope in scopes if scope)


def _metadata_scopes(event: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    trigger_context = _nested_mapping(event, "triggerContext")
    data = _nested_mapping(event, "data")
    return tuple(scope for scope in (trigger_context, event, data) if scope)


def _nested_mapping(scope: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = _mapping_get(scope, key)
    return value if isinstance(value, Mapping) else {}


def _mapping_get(scope: Mapping[str, Any], key: str) -> Any:
    if key in scope:
        return scope[key]

    normalized_key = _normalize_key(key)
    for candidate_key, value in scope.items():
        if isinstance(candidate_key, str) and _normalize_key(candidate_key) == normalized_key:
            return value

    return None


def _normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", _split_camel_case(value).lower())


def _normalize_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    value = _split_camel_case(value)
    value = re.sub(r"[^a-zA-Z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip().lower()


def _split_camel_case(value: str) -> str:
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    return re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", value)


def _has_title_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def main() -> int:
    event = json.load(sys.stdin)
    result = build_issue_title_update(event)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
