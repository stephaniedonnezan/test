"""Helpers for adding a Linear research marker to issue titles."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


RESEARCH_PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"

_CONTEXT_KEYS = ("triggerContext", "data", "issue")
_TITLE_KEYS = ("title", "name")
_ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "id")
_TRIGGER_KEYS = ("trigger", "webhookType", "action", "type", "eventType")
_UPDATED_FIELD_KEYS = (
    "updatedFields",
    "updated_fields",
    "changedFields",
    "changed_fields",
)
_EXPLICIT_NEW_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "newWorkflowState",
    "new_workflow_state",
    "statusName",
    "stateName",
    "workflowStateName",
)
_STATUS_CONTAINER_KEYS = ("state", "workflowState", "status")
_STATUS_VALUE_KEYS = ("status", "state", "workflowState")


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Build an issue title update for Linear issues moved to "to research".

    The function is intentionally side-effect free so automation runners can
    decide how to apply the returned action.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _ordered_contexts(event)
    if not _is_status_change_event(contexts):
        return None

    new_status = _first_status_candidate(contexts)
    if _normalize(new_status) != RESEARCH_STATUS:
        return None

    issue_id, title = _issue_identity(contexts)
    if not issue_id or not title:
        return None

    stripped_title = title.strip()
    if _has_research_prefix(stripped_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{RESEARCH_PREFIX}: {stripped_title}",
    }


def handle_issue_status_changed(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Compatibility entrypoint for automation runtimes."""

    return build_issue_title_update(event)


def _ordered_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return likely payload contexts while preserving useful outer metadata."""

    contexts: list[Mapping[str, Any]] = []
    seen: set[int] = set()

    def add_context(value: Any) -> None:
        if not isinstance(value, Mapping):
            return
        value_id = id(value)
        if value_id in seen:
            return
        seen.add(value_id)
        contexts.append(value)
        for key in _CONTEXT_KEYS:
            add_context(value.get(key))

    for key in _CONTEXT_KEYS:
        add_context(event.get(key))

    add_context(event)
    return contexts


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    metadata = [
        _normalize(context.get(key))
        for context in contexts
        for key in _TRIGGER_KEYS
        if _to_text(context.get(key))
    ]

    if any(_is_direct_status_change(value) for value in metadata):
        return True

    has_issue_update = any(_is_issue_update(value) for value in metadata)
    if has_issue_update:
        return _updated_fields_include_status(contexts)

    return False


def _is_direct_status_change(value: str) -> bool:
    return ("status" in value or "state" in value) and (
        "change" in value or "changed" in value
    )


def _is_issue_update(value: str) -> bool:
    if value in {"update", "updated"}:
        return True
    return "update" in value and "issue" in value


def _updated_fields_include_status(contexts: Iterable[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in _UPDATED_FIELD_KEYS:
            fields = context.get(key)
            for field in _field_values(fields):
                normalized = _normalize(field)
                compact = normalized.replace(" ", "")
                if "status" in normalized or compact in {
                    "state",
                    "stateid",
                    "workflowstate",
                    "workflowstateid",
                }:
                    return True
    return False


def _field_values(fields: Any) -> Iterable[Any]:
    if isinstance(fields, Mapping):
        yield from fields.keys()
        return
    if isinstance(fields, (list, tuple, set)):
        yield from fields
        return
    if fields is not None:
        yield fields


def _first_status_candidate(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    context_list = list(contexts)

    for key in _EXPLICIT_NEW_STATUS_KEYS:
        for context in context_list:
            text = _to_text(context.get(key))
            if text:
                return text

    for context in context_list:
        for key in _STATUS_CONTAINER_KEYS:
            value = context.get(key)
            if isinstance(value, Mapping):
                for name_key in ("name", "title"):
                    text = _to_text(value.get(name_key))
                    if text:
                        return text

    for context in context_list:
        for key in _STATUS_VALUE_KEYS:
            text = _to_text(context.get(key))
            if text:
                return text

    return None


def _issue_identity(contexts: Iterable[Mapping[str, Any]]) -> tuple[str | None, str | None]:
    for context in contexts:
        title = _first_text_value(context, _TITLE_KEYS)
        if not title:
            continue

        issue_id = _first_text_value(context, _ISSUE_ID_KEYS)
        if issue_id:
            return issue_id, title

    return None, None


def _first_text_value(context: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for key in keys:
        text = _to_text(context.get(key))
        if text:
            return text
    return None


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(RESEARCH_PREFIX.lower())


def _normalize(value: Any) -> str:
    text = _to_text(value)
    if not text:
        return ""

    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.casefold().split())


def _to_text(value: Any) -> str | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, str):
        text = value.strip()
        return text or None
    if isinstance(value, (int, float)):
        return str(value)
    return None


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
