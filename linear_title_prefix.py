"""Build Linear issue-title updates for Cursor research status changes.

The automation platform applies the returned action. This module keeps the
decision small and deterministic so it can be exercised without Linear access.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


RESEARCH_PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"

_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflowstate",
    "workflow_state",
}
_DIRECT_STATUS_CHANGE_EVENTS = {
    "statuschanged",
    "statechanged",
    "workflowstatechanged",
}
_GENERIC_UPDATE_EVENTS = {
    "update",
    "updated",
    "issueupdate",
    "issueupdated",
    "updatedissue",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update when an issue moves to "to research".

    Supported inputs include the flat Cursor automation trigger context and
    common nested Linear webhook shapes such as ``{"data": {"issue": ...}}``.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = list(_iter_contexts(event))
    if not _is_status_change_event(contexts):
        return None

    new_status = _find_new_status(contexts)
    if _normalize_status(new_status) != RESEARCH_STATUS:
        return None

    title = _find_text(contexts, ("title", "name"))
    issue_id = _find_text(
        contexts,
        ("issueId", "issue_id", "identifier", "key", "id"),
    )
    if not title or not issue_id:
        return None

    title = title.strip()
    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{RESEARCH_PREFIX}: {title}",
    }


def _iter_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return useful payload layers from outermost to innermost."""

    contexts: list[Mapping[str, Any]] = []

    def visit(value: Any) -> None:
        if not isinstance(value, Mapping) or value in contexts:
            return

        contexts.append(value)
        for key in ("triggerContext", "data", "issue", "node"):
            child = value.get(key)
            if isinstance(child, Mapping):
                visit(child)

    visit(event)
    return contexts


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    event_names = {
        _normalize_token(value)
        for context in contexts
        for key in ("trigger", "webhookType", "action", "type", "event", "eventType")
        for value in (context.get(key),)
        if isinstance(value, str)
    }

    if event_names & _DIRECT_STATUS_CHANGE_EVENTS:
        return True

    if _has_explicit_new_status(contexts):
        return True

    if event_names & _GENERIC_UPDATE_EVENTS:
        return _updated_fields_include_status(contexts)

    return False


def _has_explicit_new_status(contexts: list[Mapping[str, Any]]) -> bool:
    explicit_keys = {
        "newStatus",
        "new_status",
        "toStatus",
        "to_status",
        "statusName",
        "stateName",
        "workflowStateName",
        "workflow_state_name",
    }
    return any(key in context for context in contexts for key in explicit_keys)


def _updated_fields_include_status(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            if _field_collection_has_status(context.get(key)):
                return True

        changes = context.get("changes")
        if isinstance(changes, Mapping) and any(
            _normalize_token(key) in _STATUS_FIELD_NAMES for key in changes
        ):
            return True

        updated_from = context.get("updatedFrom") or context.get("updated_from")
        if isinstance(updated_from, Mapping) and any(
            _normalize_token(key) in _STATUS_FIELD_NAMES for key in updated_from
        ):
            return True

    return False


def _field_collection_has_status(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_token(value) in _STATUS_FIELD_NAMES

    if isinstance(value, Mapping):
        return any(_normalize_token(key) in _STATUS_FIELD_NAMES for key in value)

    if isinstance(value, list | tuple | set):
        return any(_field_collection_has_status(item) for item in value)

    return False


def _find_new_status(contexts: list[Mapping[str, Any]]) -> str | None:
    for key in (
        "newStatus",
        "new_status",
        "toStatus",
        "to_status",
        "statusName",
        "stateName",
        "workflowStateName",
        "workflow_state_name",
    ):
        value = _find_value(contexts, key)
        text = _extract_name(value)
        if text:
            return text

    for context in contexts:
        for key in ("status", "state", "workflowState", "workflow_state"):
            text = _extract_name(context.get(key))
            if text:
                return text

    return None


def _find_text(contexts: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        text = _extract_name(_find_value(contexts, key))
        if text:
            return text
    return None


def _find_value(contexts: list[Mapping[str, Any]], key: str) -> Any:
    for context in contexts:
        if key in context:
            return context[key]
    return None


def _extract_name(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            text = _extract_name(value.get(key))
            if text:
                return text

    return None


def _normalize_status(value: str | None) -> str | None:
    if value is None:
        return None
    return re.sub(r"\s+", " ", _split_words(value)).strip().lower()


def _normalize_token(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^a-z0-9]", "", _split_words(value).lower())


def _split_words(value: str) -> str:
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    return re.sub(r"[_\-\s]+", " ", value)


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(RESEARCH_PREFIX.lower())


def main() -> int:
    payload = json.load(sys.stdin)
    result = build_issue_title_update(payload)
    if result is not None:
        print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
