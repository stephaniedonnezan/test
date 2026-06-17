"""Build Linear issue title update actions for research-status transitions.

The Cursor automation runtime provides Linear webhook data in a few different
shapes. This module keeps the contract small: return an action describing the
title update when an issue enters "To Research", otherwise return ``None``.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_CONTEXT_KEYS = (
    "triggerContext",
    "data",
    "issue",
    "node",
    "object",
    "payload",
    "resource",
    "webhook",
    "changes",
    "updatedFrom",
    "updatedTo",
    "state",
    "workflowState",
    "workflow_state",
)
_TRIGGER_KEYS = ("trigger", "webhookType", "action", "type")
_NEW_STATUS_KEYS = (
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
_STATUS_FALLBACK_KEYS = ("status", "state", "workflowState", "workflow_state")
_ISSUE_ID_KEYS = ("issueId", "issue_id", "id", "identifier", "key")
_STATUS_FIELD_MARKERS = {
    "status",
    "statusid",
    "state",
    "stateid",
    "workflowstate",
    "workflowstateid",
}
_DIRECT_STATUS_TRIGGERS = {
    "statuschanged",
    "statechanged",
    "workflowstatechanged",
}
_GENERIC_UPDATE_TRIGGERS = {
    "update",
    "updated",
    "issueupdated",
    "updatedissue",
    "issueupdate",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear issue title-update action for To Research transitions.

    The returned action is intentionally serializable and side-effect free so
    callers can decide how to apply it to Linear.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = tuple(_iter_contexts(event))
    if not _is_status_change_event(contexts):
        return None

    new_status = _extract_new_status(contexts)
    if _normalize_status(new_status) != TARGET_STATUS:
        return None

    issue_id = _extract_first_string(contexts, _ISSUE_ID_KEYS)
    title = _extract_first_string(contexts, ("title",))
    if issue_id is None or title is None:
        return None

    clean_title = title.strip()
    if not clean_title or _has_research_prefix(clean_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {clean_title}",
    }


def _iter_contexts(root: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    stack: list[Mapping[str, Any]] = [root]
    seen: set[int] = set()

    while stack:
        item = stack.pop(0)
        item_id = id(item)
        if item_id in seen:
            continue
        seen.add(item_id)
        yield item

        for key in _CONTEXT_KEYS:
            value = item.get(key)
            if isinstance(value, Mapping):
                stack.append(value)
            elif isinstance(value, list):
                stack.extend(child for child in value if isinstance(child, Mapping))


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    contexts = tuple(contexts)
    trigger_tokens = {
        _normalize_token(value)
        for context in contexts
        for key in _TRIGGER_KEYS
        if (value := context.get(key)) is not None
    }

    if trigger_tokens & _DIRECT_STATUS_TRIGGERS:
        return True

    has_status_marker = _has_status_update_marker(contexts)
    if has_status_marker and (trigger_tokens & _GENERIC_UPDATE_TRIGGERS):
        return True

    return has_status_marker and not trigger_tokens


def _has_status_update_marker(contexts: Iterable[Mapping[str, Any]]) -> bool:
    return any(
        _updated_fields_include_status(context)
        or _mapping_has_status_change(context.get("changes"))
        or _mapping_has_status_change(context.get("updatedFrom"))
        or _mapping_has_status_change(context.get("updatedTo"))
        for context in contexts
    )


def _updated_fields_include_status(context: Mapping[str, Any]) -> bool:
    updated_fields = context.get("updatedFields")
    if isinstance(updated_fields, str):
        updated_fields = [updated_fields]
    if not isinstance(updated_fields, list):
        return False

    return any(_is_status_field(field) for field in updated_fields)


def _mapping_has_status_change(value: Any) -> bool:
    if not isinstance(value, Mapping):
        return False

    return any(_is_status_field(key) for key in value)


def _extract_new_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    contexts = tuple(contexts)

    explicit_status = _extract_first_string(contexts, _NEW_STATUS_KEYS)
    if explicit_status is not None:
        return explicit_status

    changed_status = _extract_status_from_changes(contexts)
    if changed_status is not None:
        return changed_status

    return _extract_named_status(contexts)


def _extract_status_from_changes(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        for key in ("changes", "updatedTo"):
            changes = context.get(key)
            if not isinstance(changes, Mapping):
                continue
            for field_name, changed_value in changes.items():
                if not _is_status_field(field_name):
                    continue
                status = _extract_status_value(changed_value)
                if status is not None:
                    return status

    return None


def _extract_named_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        for key in _STATUS_FALLBACK_KEYS:
            value = context.get(key)
            status = _extract_status_value(value)
            if status is not None:
                return status
    return None


def _extract_status_value(value: Any) -> str | None:
    if isinstance(value, str):
        clean_value = value.strip()
        return clean_value or None
    if not isinstance(value, Mapping):
        return None

    for key in (
        "newValue",
        "new_value",
        "to",
        "after",
        "current",
        "name",
        "status",
        "state",
        "workflowState",
        "workflow_state",
    ):
        status = _extract_status_value(value.get(key))
        if status is not None:
            return status

    return None


def _extract_first_string(
    contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]
) -> str | None:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(TITLE_PREFIX.casefold())


def _is_status_field(value: Any) -> bool:
    if not isinstance(value, str):
        return False

    normalized = _normalize_token(value)
    return normalized in _STATUS_FIELD_MARKERS


def _normalize_status(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    return " ".join(_words(value))


def _normalize_token(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    return "".join(_words(value))


def _words(value: str) -> list[str]:
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    return re.findall(r"[a-z0-9]+", value.casefold())


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
