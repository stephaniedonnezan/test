"""Build Linear issue title updates for research status transitions."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any, Optional


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"


def build_issue_title_update(event: Optional[Mapping[str, Any]]) -> Optional[dict[str, str]]:
    """Return a title update when a Linear issue moves to "to research".

    The automation trigger can pass Linear fields either at the top level or
    nested under triggerContext/data/issue. This function accepts the common
    webhook shapes and returns a side-effect-free action for the caller to
    execute.
    """

    if not isinstance(event, Mapping):
        return None

    issue = _issue_payload(event)
    context = _context_payload(event, issue)

    if not _is_status_change_event(context):
        return None

    if _normalize_status(_first_present(context, ("newStatus", "new_status", "status"))) != TARGET_STATUS:
        status_from_state = _first_present_mapping(context, ("state", "workflowState"))
        if _normalize_status(_mapping_name(status_from_state)) != TARGET_STATUS:
            return None

    issue_id = _clean_string(_first_present(context, ("id", "issueId", "issue_id", "identifier")))
    title = _clean_string(_first_present(context, ("title", "name")))
    if not issue_id or not title:
        return None

    if _has_prefix(title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _issue_payload(event: Mapping[str, Any]) -> Mapping[str, Any]:
    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            return issue
        return data

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        return issue

    return {}


def _context_payload(event: Mapping[str, Any], issue: Mapping[str, Any]) -> dict[str, Any]:
    context: dict[str, Any] = {}
    context.update(issue)

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        context.update(trigger_context)

    context.update(event)
    return context


def _is_status_change_event(context: Mapping[str, Any]) -> bool:
    trigger = _normalize_token(_first_present(context, ("trigger", "webhookType", "action", "type")))
    if trigger in {"statuschanged", "statuschange", "statechanged", "statechange"}:
        return True

    if trigger in {"issueupdated", "updatedissue", "updateissue"}:
        return _updated_fields_include_status(context.get("updatedFields"))

    return False


def _updated_fields_include_status(updated_fields: Any) -> bool:
    if isinstance(updated_fields, str):
        fields = [updated_fields]
    elif isinstance(updated_fields, Mapping):
        fields = updated_fields.keys()
    elif isinstance(updated_fields, (list, tuple, set, frozenset)):
        fields = updated_fields
    else:
        return False

    return any(_normalize_token(field) in {"status", "state", "workflowstate"} for field in fields)


def _first_present(mapping: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = mapping.get(key)
        if value is not None:
            return value
    return None


def _first_present_mapping(mapping: Mapping[str, Any], keys: tuple[str, ...]) -> Optional[Mapping[str, Any]]:
    value = _first_present(mapping, keys)
    return value if isinstance(value, Mapping) else None


def _mapping_name(mapping: Optional[Mapping[str, Any]]) -> Any:
    if not mapping:
        return None
    return _first_present(mapping, ("name", "title"))


def _clean_string(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None

    value = value.strip()
    return value or None


def _normalize_status(value: Any) -> Optional[str]:
    cleaned = _clean_string(value)
    if cleaned is None:
        return None

    return re.sub(r"[\W_]+", " ", _split_camel_case(cleaned)).strip().lower()


def _normalize_token(value: Any) -> Optional[str]:
    cleaned = _clean_string(value)
    if cleaned is None:
        return None

    return re.sub(r"[\W_]+", "", _split_camel_case(cleaned)).lower()


def _split_camel_case(value: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)


def _has_prefix(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())
