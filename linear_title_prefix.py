"""Build Linear issue title updates for Cursor research status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELDS = {
    "status",
    "statusid",
    "statusname",
    "state",
    "stateid",
    "statename",
    "workflowstate",
    "workflowstateid",
    "workflowstatename",
}
_DIRECT_STATUS_CHANGE_TRIGGERS = {
    "statuschanged",
    "statuschange",
    "statechanged",
    "statechange",
    "workflowstatechanged",
    "workflowstatechange",
}
_ISSUE_UPDATE_TRIGGERS = {
    "issueupdated",
    "updatedissue",
    "update",
    "updated",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update action when an issue moves into "to research"."""

    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_change(contexts):
        return None

    status = _find_status(contexts)
    if _normalize_status(status) != TARGET_STATUS:
        return None

    issue_id = _clean_string(_find_first(contexts, ("issueId", "issue_id", "id", "identifier", "key")))
    title = _clean_string(_find_first(contexts, ("title", "name")))
    if not issue_id or not title:
        return None

    if _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = [event]

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        contexts.insert(0, trigger_context)

    data = event.get("data")
    if isinstance(data, Mapping):
        contexts.append(data)
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            contexts.append(issue)

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        contexts.append(issue)

    return contexts


def _is_status_change(contexts: list[Mapping[str, Any]]) -> bool:
    if any(_normalize_token(value) in _DIRECT_STATUS_CHANGE_TRIGGERS for value in _event_type_values(contexts)):
        return True

    if not any(_normalize_token(value) in _ISSUE_UPDATE_TRIGGERS for value in _event_type_values(contexts)):
        return False

    return any(_status_field_changed(context) for context in contexts)


def _event_type_values(contexts: list[Mapping[str, Any]]) -> list[Any]:
    values: list[Any] = []
    for context in contexts:
        for key in ("trigger", "action", "webhookType", "type"):
            if key in context:
                values.append(context[key])
    return values


def _status_field_changed(context: Mapping[str, Any]) -> bool:
    updated_fields = context.get("updatedFields")
    if isinstance(updated_fields, (list, tuple, set)):
        return any(_normalize_field_name(field) in _STATUS_FIELDS for field in updated_fields)
    if isinstance(updated_fields, str):
        return _normalize_field_name(updated_fields) in _STATUS_FIELDS

    for key in ("updatedFrom", "changes", "changedFields"):
        changed = context.get(key)
        if isinstance(changed, Mapping):
            return any(_normalize_field_name(field) in _STATUS_FIELDS for field in changed)
        if isinstance(changed, (list, tuple, set)):
            return any(_normalize_field_name(field) in _STATUS_FIELDS for field in changed)

    return False


def _find_status(contexts: list[Mapping[str, Any]]) -> Any:
    for key in ("newStatus", "new_status", "statusName", "stateName", "workflowStateName"):
        value = _find_first(contexts, (key,))
        if value is not None:
            return value

    for context in contexts:
        for key in ("status", "state", "workflowState"):
            value = context.get(key)
            if isinstance(value, Mapping):
                name = value.get("name")
                if name is not None:
                    return name
            elif value is not None:
                return value

    return None


def _find_first(contexts: list[Mapping[str, Any]], keys: tuple[str, ...]) -> Any:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if value is not None:
                return value
    return None


def _clean_string(value: Any) -> str | None:
    if value is None:
        return None
    stripped = str(value).strip()
    return stripped or None


def _has_prefix(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())


def _normalize_status(value: Any) -> str | None:
    cleaned = _clean_string(value)
    if cleaned is None:
        return None
    return re.sub(r"[\s_-]+", " ", _split_camel_case(cleaned)).strip().casefold()


def _normalize_token(value: Any) -> str:
    cleaned = _clean_string(value)
    if cleaned is None:
        return ""
    return re.sub(r"[^a-z0-9]", "", _split_camel_case(cleaned).casefold())


def _normalize_field_name(value: Any) -> str:
    cleaned = _clean_string(value)
    if cleaned is None:
        return ""
    return re.sub(r"[^a-z0-9]", "", _split_camel_case(cleaned).casefold())


def _split_camel_case(value: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)


def main() -> int:
    event = json.load(sys.stdin)
    result = build_issue_title_update(event)
    if result is not None:
        print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
