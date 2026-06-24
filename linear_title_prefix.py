"""Build Linear issue title updates for Cursor research automation."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {"status", "state", "workflow state", "workflowstate"}
_DIRECT_STATUS_CHANGE_EVENTS = {
    "status changed",
    "status change",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
}
_GENERIC_UPDATE_EVENTS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue-title update action when a Linear issue enters research."""

    if not isinstance(event, Mapping):
        return None

    contexts = list(_prioritized_contexts(event))
    if not _is_status_change_event(contexts):
        return None

    status = _extract_new_status(contexts)
    if _normalize(status) != TARGET_STATUS:
        return None

    issue_id = _extract_first_text(contexts, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _extract_first_text(contexts, ("title",))
    if not issue_id or not title:
        return None

    stripped_title = title.strip()
    if _has_research_prefix(stripped_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {stripped_title}",
    }


def _prioritized_contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    root = event
    trigger_context = _mapping_at(root, "triggerContext")
    data = _mapping_at(root, "data")
    issue = _mapping_at(root, "issue")

    yield from _yield_if_mapping(trigger_context)
    yield from _yield_if_mapping(_mapping_at(trigger_context, "issue"))
    yield from _yield_if_mapping(_mapping_at(_mapping_at(trigger_context, "data"), "issue"))
    yield from _yield_if_mapping(issue)
    yield from _yield_if_mapping(_mapping_at(data, "issue"))
    yield from _yield_if_mapping(data)
    yield root


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    contexts = list(contexts)
    event_names = {
        _normalize(context.get(key))
        for context in contexts
        for key in ("trigger", "action", "type", "webhookType", "eventType")
    }

    if event_names & _DIRECT_STATUS_CHANGE_EVENTS:
        return True

    if event_names & _GENERIC_UPDATE_EVENTS:
        return any(_has_status_change_marker(context) for context in contexts)

    return False


def _has_status_change_marker(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, nested_value in value.items():
            normalized_key = _normalize(key)
            if normalized_key in {"updated fields", "changed fields", "updatedfields", "changedfields"}:
                if any(_is_status_field_name(field) for field in _iter_field_names(nested_value)):
                    return True
            if normalized_key == "changes" and isinstance(nested_value, Mapping):
                if any(_is_status_field_name(field) for field in nested_value):
                    return True
            if _has_status_change_marker(nested_value):
                return True
    elif isinstance(value, list):
        return any(_has_status_change_marker(item) for item in value)

    return False


def _extract_new_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    contexts = list(contexts)
    explicit_keys = (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "newWorkflowState",
        "new_workflow_state",
    )
    status = _extract_first_text(contexts, explicit_keys)
    if status:
        return status

    changed_status = _extract_status_from_changes(contexts)
    if changed_status:
        return changed_status

    return _extract_first_text(contexts, ("status", "state", "workflowState", "workflow_state"))


def _extract_status_from_changes(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        changes = context.get("changes")
        if not isinstance(changes, Mapping):
            continue
        for key, value in changes.items():
            if not _is_status_field_name(key):
                continue
            status = _extract_change_target(value)
            if status:
                return status
    return None


def _extract_change_target(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("to", "new", "after", "current", "value", "name"):
            if key in value:
                text = _text(value[key])
                if text:
                    return text
    return _text(value)


def _extract_first_text(contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for context in contexts:
        for key in keys:
            if key not in context:
                continue
            text = _text(context[key])
            if text:
                return text
    return None


def _iter_field_names(value: Any) -> Iterable[Any]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, Mapping):
        for key in ("name", "field", "key"):
            if key in value:
                yield value[key]
        for nested_value in value.values():
            yield from _iter_field_names(nested_value)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_field_names(item)


def _is_status_field_name(value: Any) -> bool:
    return _normalize(value) in _STATUS_FIELD_NAMES


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def _mapping_at(value: Mapping[str, Any] | None, key: str) -> Mapping[str, Any] | None:
    if isinstance(value, Mapping) and isinstance(value.get(key), Mapping):
        return value[key]
    return None


def _yield_if_mapping(value: Mapping[str, Any] | None) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value


def _text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, Mapping):
        for key in ("name", "title", "identifier", "key", "id"):
            if key in value:
                text = _text(value[key])
                if text:
                    return text
        return None
    return str(value).strip() or None


def _normalize(value: Any) -> str:
    text = _text(value)
    if not text:
        return ""
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
