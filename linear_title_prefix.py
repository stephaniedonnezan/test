"""Build Linear issue title update actions for research-status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow state"}
_NEW_STATUS_FIELDS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "newWorkflowState",
    "new_workflow_state",
    "toStatus",
    "to_status",
    "toState",
    "to_state",
)
_ISSUE_ID_FIELDS = ("issueId", "issue_id", "identifier", "id")


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to To Research."""
    if not isinstance(event, Mapping):
        return None

    contexts = list(_ordered_contexts(event))
    if not _is_status_change_event(contexts):
        return None
    if _normalized_status(_new_status(contexts)) != TARGET_STATUS:
        return None

    title_context = _first_context_with_string(contexts, "title")
    if title_context is None:
        return None

    title = _clean_string(title_context.get("title"))
    if not title or _has_prefix(title):
        return None

    issue_id = _issue_id(title_context, contexts)
    if not issue_id:
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _ordered_contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely Linear issue/status contexts from most to least specific."""
    yielded: set[int] = set()

    def emit(value: Any) -> Iterable[Mapping[str, Any]]:
        if isinstance(value, Mapping) and id(value) not in yielded:
            yielded.add(id(value))
            yield value

    for key in ("triggerContext", "data", "issue"):
        container = event.get(key)
        if isinstance(container, Mapping):
            for nested_key in ("issue", "data"):
                yield from emit(container.get(nested_key))
            yield from emit(container)

    yield from emit(event)

    for value in _walk_mappings(event):
        yield from emit(value)


def _walk_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        for child in value.values():
            if isinstance(child, Mapping):
                yield child
                yield from _walk_mappings(child)
            elif isinstance(child, list):
                for item in child:
                    yield from _walk_mappings(item)


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("trigger", "event", "eventType", "webhookType", "type"):
            signal = _normalized_status(context.get(key))
            if "status changed" in signal or "state changed" in signal:
                return True

        action = _normalized_status(context.get("action"))
        if action in {"update", "updated", "issue updated", "updated issue"}:
            if _updated_fields_include_status(context):
                return True

    return False


def _updated_fields_include_status(context: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        fields = context.get(key)
        if isinstance(fields, Mapping):
            field_names = fields.keys()
        elif isinstance(fields, list | tuple | set):
            field_names = fields
        else:
            continue

        for field in field_names:
            if _normalized_field_name(field) in _STATUS_FIELD_NAMES:
                return True

    return False


def _new_status(contexts: list[Mapping[str, Any]]) -> Any:
    for context in contexts:
        for key in _NEW_STATUS_FIELDS:
            value = context.get(key)
            if _clean_string(value):
                return value

    for context in contexts:
        for key in ("status", "state", "workflowState", "workflow_state"):
            value = context.get(key)
            if isinstance(value, Mapping):
                name = value.get("name")
                if _clean_string(name):
                    return name
            elif _clean_string(value):
                return value

    return None


def _issue_id(title_context: Mapping[str, Any], contexts: list[Mapping[str, Any]]) -> str | None:
    for key in _ISSUE_ID_FIELDS:
        value = _clean_string(title_context.get(key))
        if value:
            return value

    for context in contexts:
        if not _looks_like_issue_context(context):
            continue
        for key in _ISSUE_ID_FIELDS:
            value = _clean_string(context.get(key))
            if value:
                return value

    return None


def _looks_like_issue_context(context: Mapping[str, Any]) -> bool:
    return any(key in context for key in ("title", "status", "state", "workflowState", "workflow_state"))


def _first_context_with_string(
    contexts: list[Mapping[str, Any]], key: str
) -> Mapping[str, Any] | None:
    for context in contexts:
        if _clean_string(context.get(key)):
            return context
    return None


def _has_prefix(title: str) -> bool:
    return title.lstrip().lower().startswith(PREFIX.lower())


def _normalized_status(value: Any) -> str:
    text = _clean_string(value)
    if not text:
        return ""

    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def _normalized_field_name(value: Any) -> str:
    return _normalized_status(value).replace(" ", "")


def _clean_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
