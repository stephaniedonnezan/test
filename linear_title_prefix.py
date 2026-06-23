"""Build Linear issue title updates for research-status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"

_STATUS_FIELD_NAMES = frozenset({"status", "state", "workflowstate", "workflow_state"})
_DIRECT_STATUS_CHANGE_EVENTS = frozenset(
    {
        "status changed",
        "status change",
        "state changed",
        "state change",
        "workflow state changed",
        "workflow state change",
    }
)
_GENERIC_UPDATE_EVENTS = frozenset(
    {
        "update",
        "updated",
        "issue update",
        "issue updated",
        "updated issue",
    }
)


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear issue title update when an issue moves to research."""

    if not isinstance(event, Mapping):
        return None

    contexts = list(_collect_contexts(event))
    if not _is_status_change_event(contexts):
        return None

    if _normalize(_extract_status(contexts)) != TARGET_STATUS:
        return None

    issue_id = _extract_first_text(contexts, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _extract_first_text(contexts, ("title",))
    if not issue_id or not title or _has_research_prefix(title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _collect_contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely payload objects in priority order, then remaining mappings."""

    yielded: set[int] = set()

    def yield_once(value: Any) -> Iterable[Mapping[str, Any]]:
        if isinstance(value, Mapping) and id(value) not in yielded:
            yielded.add(id(value))
            yield value

    yield from yield_once(event)

    for key in (
        "automation_trigger_info",
        "automationTriggerInfo",
        "triggerContext",
        "trigger_context",
    ):
        yield from yield_once(event.get(key))

    for parent_key in ("automation_trigger_info", "automationTriggerInfo"):
        parent = event.get(parent_key)
        if isinstance(parent, Mapping):
            for child_key in ("triggerContext", "trigger_context"):
                yield from yield_once(parent.get(child_key))

    for key in ("data", "issue", "node", "payload"):
        value = event.get(key)
        yield from yield_once(value)
        if isinstance(value, Mapping):
            yield from yield_once(value.get("issue"))

    yield from _walk_mappings(event, yielded)


def _walk_mappings(value: Any, yielded: set[int]) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        if id(value) not in yielded:
            yielded.add(id(value))
            yield value
        for child in value.values():
            yield from _walk_mappings(child, yielded)
    elif isinstance(value, list | tuple):
        for item in value:
            yield from _walk_mappings(item, yielded)


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    event_names = {
        _normalize(context.get(key))
        for context in contexts
        for key in ("trigger", "triggerType", "webhookType", "action", "type", "eventType")
    }
    event_names.discard("")

    if event_names & _DIRECT_STATUS_CHANGE_EVENTS:
        return True

    if event_names & _GENERIC_UPDATE_EVENTS:
        return any(_contains_status_change_marker(context) for context in contexts)

    return False


def _contains_status_change_marker(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized_key = _normalize_key(key)
            if normalized_key in {"updatedfields", "changedfields"}:
                if _contains_status_field_name(child):
                    return True
            if normalized_key in {"changes", "updatedproperties", "changedproperties"}:
                if _contains_status_field_name(child):
                    return True
            if _contains_status_change_marker(child):
                return True
    elif isinstance(value, list | tuple | set):
        return any(_contains_status_change_marker(item) for item in value)

    return False


def _contains_status_field_name(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_key(value) in _STATUS_FIELD_NAMES
    if isinstance(value, Mapping):
        return any(
            _normalize_key(key) in _STATUS_FIELD_NAMES or _contains_status_field_name(child)
            for key, child in value.items()
        )
    if isinstance(value, list | tuple | set):
        return any(_contains_status_field_name(item) for item in value)
    return False


def _extract_status(contexts: list[Mapping[str, Any]]) -> str | None:
    explicit_keys = (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "newWorkflowState",
        "new_workflow_state",
        "toStatus",
        "to_status",
    )
    status = _extract_first_text(contexts, explicit_keys)
    if status:
        return status

    status = _extract_status_from_changes(contexts)
    if status:
        return status

    return _extract_first_text(contexts, ("status", "state", "workflowState", "workflow_state"))


def _extract_status_from_changes(contexts: list[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        for key in ("changes", "updatedProperties", "changedProperties"):
            status = _status_from_change_value(context.get(key))
            if status:
                return status
    return None


def _status_from_change_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if _normalize_key(key) in _STATUS_FIELD_NAMES:
                status = _status_from_change_leaf(child)
                if status:
                    return status
            status = _status_from_change_value(child)
            if status:
                return status
    elif isinstance(value, list | tuple):
        for item in value:
            status = _status_from_change_value(item)
            if status:
                return status
    return None


def _status_from_change_leaf(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, Mapping):
        for key in ("to", "new", "newValue", "value", "name"):
            text = _text_value(value.get(key))
            if text:
                return text
    return None


def _extract_first_text(contexts: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    normalized_keys = {_normalize_key(key) for key in keys}

    for context in contexts:
        for key, value in context.items():
            if _normalize_key(key) in normalized_keys:
                text = _text_value(value)
                if text:
                    return text
    return None


def _text_value(value: Any) -> str | None:
    if isinstance(value, str):
        text = value.strip()
        return text or None
    if isinstance(value, int):
        return str(value)
    if isinstance(value, Mapping):
        for key in ("name", "title", "identifier", "key", "id"):
            text = _text_value(value.get(key))
            if text:
                return text
    return None


def _has_research_prefix(title: str) -> bool:
    return title.strip().casefold().startswith(PREFIX.casefold())


def _normalize(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.casefold().split())


def _normalize_key(value: Any) -> str:
    return _normalize(value).replace(" ", "")


def main() -> int:
    """Read a JSON payload from stdin and print the requested title update."""

    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 2

    update = build_issue_title_update(event)
    print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
