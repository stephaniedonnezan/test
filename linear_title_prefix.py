"""Build title update actions for Linear issue status changes.

The automation runner supplies Linear webhook context as JSON.  This module
keeps the side-effect boundary explicit: it returns a small action payload for
the caller to apply to Linear, or ``None`` when the event should be ignored.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


RESEARCH_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_CONTEXT_KEYS = ("triggerContext", "data", "payload", "webhook", "event")
_ISSUE_KEYS = ("issue", "entity")
_EXPLICIT_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "toStatus",
    "to_status",
    "toState",
    "to_state",
)
_STATUS_KEYS = ("status", "state", "workflowState", "workflow_state")
_ISSUE_ID_KEYS = ("issueId", "issue_id", "id", "identifier")
_TITLE_KEYS = ("title", "name")
_TRIGGER_KEYS = ("trigger", "eventName", "eventType", "type", "action")
_UPDATED_FIELD_KEYS = (
    "updatedFields",
    "updated_fields",
    "changedFields",
    "changed_fields",
    "changes",
)
_STATUS_FIELD_NAMES = {"status", "state", "workflow state", "workflowstate"}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return an issue title update action when an issue moves to To Research.

    The returned shape is intentionally transport-agnostic so the surrounding
    automation can decide how to apply it:

    ``{"action": "update_issue_title", "issueId": "...", "title": "..."}``
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _collect_contexts(event)
    if not _is_status_change_event(contexts):
        return None

    new_status = _extract_status(contexts)
    if _normalize_text(new_status) != _normalize_text(TARGET_STATUS):
        return None

    issue_id = _extract_text(contexts, _ISSUE_ID_KEYS)
    title = _extract_text(contexts, _TITLE_KEYS)
    if not issue_id or not title:
        return None

    clean_title = title.strip()
    if _has_research_prefix(clean_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{RESEARCH_PREFIX}: {clean_title}",
    }


def _collect_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Collect likely metadata and issue containers in priority order."""

    contexts: list[Mapping[str, Any]] = []
    seen: set[int] = set()

    def add(mapping: Mapping[str, Any]) -> None:
        marker = id(mapping)
        if marker not in seen:
            seen.add(marker)
            contexts.append(mapping)

    add(event)

    queue = [event]
    for mapping in queue:
        for key in (*_CONTEXT_KEYS, *_ISSUE_KEYS):
            child = mapping.get(key)
            if isinstance(child, Mapping):
                add(child)
                queue.append(child)

    return contexts


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    saw_issue_update = False

    for context in contexts:
        for key in _TRIGGER_KEYS:
            trigger = context.get(key)
            normalized_trigger = _normalize_text(_status_name(trigger))
            if normalized_trigger in {"status change", "status changed"}:
                return True
            if normalized_trigger in {"update", "updated", "issue update", "issue updated"}:
                saw_issue_update = True

        if _updated_fields_include_status(context):
            return True

    return saw_issue_update and any(_updated_fields_include_status(context) for context in contexts)


def _updated_fields_include_status(context: Mapping[str, Any]) -> bool:
    for key in _UPDATED_FIELD_KEYS:
        if key not in context:
            continue
        if _field_names_include_status(context[key]):
            return True
    return False


def _field_names_include_status(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_text(value) in _STATUS_FIELD_NAMES

    if isinstance(value, Mapping):
        return any(_field_names_include_status(key) for key in value.keys())

    if isinstance(value, Iterable):
        return any(_field_names_include_status(item) for item in value)

    return False


def _extract_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    context_list = list(contexts)
    for key_group in (_EXPLICIT_STATUS_KEYS, _STATUS_KEYS):
        for context in context_list:
            status = _extract_status_from_context(context, key_group)
            if status:
                return status
    return None


def _extract_status_from_context(
    context: Mapping[str, Any], keys: Iterable[str]
) -> str | None:
    for key in keys:
        if key not in context:
            continue
        status = _status_name(context[key])
        if status:
            return status.strip()
    return None


def _status_name(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        for key in ("name", "title", "status", "state"):
            status = _status_name(value.get(key))
            if status:
                return status
    return None


def _extract_text(contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _has_research_prefix(title: str) -> bool:
    return title.lstrip().lower().startswith(RESEARCH_PREFIX.lower())


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""
    with_spaces = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    with_spaces = re.sub(r"[_\-/]+", " ", with_spaces)
    with_spaces = re.sub(r"[^0-9A-Za-z]+", " ", with_spaces)
    return re.sub(r"\s+", " ", with_spaces).strip().lower()


def main() -> int:
    """Read a JSON event from stdin and print the action payload as JSON."""

    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(build_issue_title_update(event), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
