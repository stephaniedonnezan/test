"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"

_EXPLICIT_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "newWorkflowState",
    "new_workflow_state",
    "statusName",
    "status_name",
    "stateName",
    "state_name",
    "workflowStateName",
    "workflow_state_name",
)
_FALLBACK_STATUS_KEYS = ("status", "state", "workflowState", "workflow_state")
_STATUS_CHANGE_FIELDS = {
    "status",
    "statusid",
    "statusname",
    "state",
    "stateid",
    "statename",
    "workflowstate",
    "workflowstateid",
    "workflowstatename",
    "workflow_state",
    "workflow_state_id",
    "workflow_state_name",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue title update action when a Linear issue enters research."""

    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_change(contexts):
        return None

    status = _extract_status(contexts)
    if _normalize_status(status) != RESEARCH_STATUS:
        return None

    issue_contexts = _issue_contexts(event)
    issue_id = _extract_text(issue_contexts, ("id", "issueId", "issue_id", "identifier"))
    title = _extract_text(issue_contexts, ("title", "name"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return useful payload scopes from outermost metadata to nested issue data."""

    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)

    add(event)
    trigger_context = event.get("triggerContext")
    add(trigger_context)
    data = event.get("data")
    add(data)

    for parent in (trigger_context, data, event):
        if isinstance(parent, Mapping):
            issue = parent.get("issue")
            add(issue)
            if isinstance(parent.get("data"), Mapping):
                add(parent["data"])
                add(parent["data"].get("issue"))

    return contexts


def _issue_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Prefer Linear issue scopes over wrapper metadata when extracting identity."""

    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)

    trigger_context = event.get("triggerContext")
    data = event.get("data")

    add(trigger_context)
    for parent in (trigger_context, data, event):
        if isinstance(parent, Mapping):
            add(parent.get("issue"))
            nested_data = parent.get("data")
            if isinstance(nested_data, Mapping):
                add(nested_data.get("issue"))
                add(nested_data)

    add(data)
    add(event)
    return contexts


def _is_status_change(contexts: list[Mapping[str, Any]]) -> bool:
    trigger_values = []
    updated_fields = []

    for context in contexts:
        trigger_values.extend(
            str(context[key])
            for key in ("trigger", "action", "type", "webhookType", "webhook_type")
            if key in context and context[key] is not None
        )
        updated_fields.extend(_as_list(context.get("updatedFields")))
        updated_fields.extend(_as_list(context.get("updated_fields")))
        updated_fields.extend(_as_list(context.get("changedFields")))
        updated_fields.extend(_as_list(context.get("changed_fields")))
        updated_from = context.get("updatedFrom") or context.get("updated_from")
        if isinstance(updated_from, Mapping):
            updated_fields.extend(str(key) for key in updated_from)

    normalized_triggers = {_normalize_token(value) for value in trigger_values}
    if normalized_triggers & {"statuschanged", "statuschange", "statusupdated"}:
        return True

    issue_update_triggers = {
        "update",
        "updated",
        "issueupdate",
        "issueupdated",
        "updatedissue",
    }
    if normalized_triggers & issue_update_triggers:
        return any(_normalize_token(field) in _STATUS_CHANGE_FIELDS for field in updated_fields)

    return False


def _extract_status(contexts: list[Mapping[str, Any]]) -> str | None:
    for key in _EXPLICIT_STATUS_KEYS:
        value = _extract_value(contexts, (key,))
        text = _value_text(value)
        if text:
            return text

    for context in contexts:
        for key in _FALLBACK_STATUS_KEYS:
            text = _value_text(context.get(key))
            if text:
                return text

    return None


def _extract_text(contexts: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    return _value_text(_extract_value(contexts, keys))


def _extract_value(contexts: list[Mapping[str, Any]], keys: tuple[str, ...]) -> Any:
    for context in contexts:
        for key in keys:
            if key in context and context[key] is not None:
                return context[key]
    return None


def _value_text(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        for key in ("name", "title", "id", "identifier"):
            if key in value and value[key] is not None:
                return str(value[key])
    if value is not None and not isinstance(value, (list, tuple, set, dict)):
        return str(value)
    return None


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, Mapping):
        return list(value)
    if isinstance(value, (list, tuple, set)):
        return list(value)
    return [value]


def _normalize_status(value: str | None) -> str | None:
    if not value:
        return None
    return re.sub(r"[_\-\s]+", " ", _split_camel_case(value).strip().lower()).strip()


def _normalize_token(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", _split_camel_case(str(value)).lower())


def _split_camel_case(value: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def main() -> int:
    payload = json.load(sys.stdin)
    result = build_issue_title_update(payload)
    if result is not None:
        print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
