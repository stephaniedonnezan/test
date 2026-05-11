"""Build Linear issue title updates for Cursor research automation."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue enters research.

    The automation runner is expected to perform the returned action. Events
    that are not status changes to "to research", are missing issue metadata,
    or are already prefixed are ignored.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    if _normalize_words(_new_status(event)) != TARGET_STATUS:
        return None

    issue_id = _clean_string(_first_lookup(event, ("id", "issueId", "issue_id", "identifier")))
    title = _clean_string(_first_lookup(event, ("title",)))
    if not issue_id or not title:
        return None

    if title.lower().startswith(TITLE_PREFIX.lower()):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    for key in ("trigger", "webhookType", "eventType"):
        value = _first_lookup(event, (key,))
        if _normalize_words(value) in {"status changed", "status change"}:
            return True

    action = _normalize_words(_first_lookup(event, ("action",)))
    event_type = _normalize_words(_first_lookup(event, ("type", "webhookType")))
    if action in {"issue updated", "updated issue"}:
        return _updated_fields_include_status(event)
    if action in {"update", "updated"} and event_type in {"issue", "issue updated"}:
        return _updated_fields_include_status(event)

    return _updated_fields_include_status(event)


def _updated_fields_include_status(event: Mapping[str, Any]) -> bool:
    for value in _lookup_all(
        event,
        (
            "updatedFields",
            "updated_fields",
            "changedFields",
            "changed_fields",
            "updatedFrom",
            "updated_from",
            "changes",
        ),
    ):
        if _field_collection_mentions_status(value):
            return True
    return False


def _field_collection_mentions_status(value: Any) -> bool:
    status_names = {"status", "state", "state id", "workflow state", "workflow state id"}
    if isinstance(value, Mapping):
        return any(_normalize_words(key) in status_names for key in value)
    if isinstance(value, str):
        return _normalize_words(value) in status_names
    if isinstance(value, Iterable):
        return any(_normalize_words(item) in status_names for item in value)
    return False


def _new_status(event: Mapping[str, Any]) -> Any:
    direct_status = _first_lookup(event, ("newStatus", "new_status", "status"))
    if direct_status is not None:
        return _named_value(direct_status)

    state = _first_lookup(event, ("state", "workflowState", "workflow_state"))
    return _named_value(state)


def _named_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        named = _lookup_in_mapping(value, ("name", "title"))
        if named is not None:
            return named
    return value


def _first_lookup(event: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    for value in _lookup_all(event, keys):
        if value is not None:
            return value
    return None


def _lookup_all(event: Mapping[str, Any], keys: tuple[str, ...]) -> Iterable[Any]:
    for mapping in _iter_mappings(event):
        value = _lookup_in_mapping(mapping, keys)
        if value is not None:
            yield value


def _iter_mappings(root: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    stack = [root]
    seen: set[int] = set()

    while stack:
        current = stack.pop(0)
        if not isinstance(current, Mapping) or id(current) in seen:
            continue
        seen.add(id(current))
        yield current

        for key in (
            "triggerContext",
            "trigger_context",
            "data",
            "issue",
            "state",
            "workflowState",
            "workflow_state",
        ):
            child = _lookup_in_mapping(current, (key,))
            if isinstance(child, Mapping):
                stack.append(child)


def _lookup_in_mapping(mapping: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in mapping:
            return mapping[key]

    normalized_keys = {_normalize_key(key) for key in keys}
    for key, value in mapping.items():
        if isinstance(key, str) and _normalize_key(key) in normalized_keys:
            return value
    return None


def _normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _normalize_words(value: Any) -> str:
    if value is None:
        return ""

    text = str(value).strip()
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def _clean_string(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()
