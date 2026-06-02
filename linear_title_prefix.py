"""Build Linear issue title updates for issues moved into research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_MARKER = "Cursor researching"
TITLE_PREFIX = f"{TITLE_MARKER}: "

_STATUS_CHANGE_FIELDS = {"status", "state", "workflowstate", "workflow_state"}
_NEW_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "newWorkflowState",
    "new_workflow_state",
    "newWorkflowStateName",
    "new_workflow_state_name",
)
_STATUS_KEYS = ("status", "state", "workflowState", "workflow_state")
_ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "id")
_TITLE_KEYS = ("title", "name")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to To Research.

    The automation runtime can pass either a flat trigger context or a nested
    Linear webhook payload. This function accepts both shapes and returns a
    small action object that a caller can apply to Linear.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = list(_collect_contexts(event))
    if not _is_status_change_event(contexts):
        return None

    if _normalize(_extract_status(contexts)) != "to research":
        return None

    title = _extract_title(contexts)
    if title is None or _has_research_marker(title):
        return None

    issue_id = _extract_issue_id(contexts)
    if issue_id is None:
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}{title}",
    }


def _collect_contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield useful payload dictionaries from outermost to innermost."""

    queue: list[Mapping[str, Any]] = [event]
    seen: set[int] = set()

    while queue:
        context = queue.pop(0)
        context_id = id(context)
        if context_id in seen:
            continue
        seen.add(context_id)
        yield context

        for key in ("triggerContext", "payload", "webhook", "data", "issue"):
            value = context.get(key)
            if isinstance(value, Mapping):
                queue.append(value)


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    contexts = list(contexts)

    for context in contexts:
        for key in ("trigger", "event", "eventType", "webhookTrigger"):
            if _normalize(context.get(key)) in {"status changed", "status change"}:
                return True

    for context in contexts:
        action = _normalize(_first_present(context, ("action", "type", "webhookType")))
        if action in {"update", "updated", "issue updated", "updated issue"}:
            return _updated_fields_include_status(context)

    return any(_updated_fields_include_status(context) for context in contexts)


def _updated_fields_include_status(context: Mapping[str, Any]) -> bool:
    raw_fields = _first_present(
        context,
        (
            "updatedFields",
            "updated_fields",
            "changedFields",
            "changed_fields",
        ),
    )

    if isinstance(raw_fields, str):
        fields = [raw_fields]
    elif isinstance(raw_fields, Mapping):
        fields = raw_fields.keys()
    elif isinstance(raw_fields, Iterable):
        fields = raw_fields
    else:
        return False

    return any(_field_key(field) in _STATUS_CHANGE_FIELDS for field in fields)


def _extract_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    contexts = list(contexts)

    for key in _NEW_STATUS_KEYS:
        for context in contexts:
            status = _status_name(context.get(key))
            if status is not None:
                return status

    for key in _STATUS_KEYS:
        for context in contexts:
            status = _status_name(context.get(key))
            if status is not None:
                return status

    return None


def _extract_title(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        for key in _TITLE_KEYS:
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _extract_issue_id(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    contexts = list(contexts)

    for context in contexts:
        if _extract_title((context,)) is None:
            continue
        issue_id = _issue_id_from_context(context)
        if issue_id is not None:
            return issue_id

    for context in contexts:
        issue_id = _issue_id_from_context(context)
        if issue_id is not None:
            return issue_id

    return None


def _issue_id_from_context(context: Mapping[str, Any]) -> str | None:
    for key in _ISSUE_ID_KEYS:
        value = context.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _status_name(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    if isinstance(value, Mapping):
        for key in ("name", "title", "status", "state"):
            nested_value = value.get(key)
            if isinstance(nested_value, str) and nested_value.strip():
                return nested_value.strip()
    return None


def _first_present(context: Mapping[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        if key in context:
            return context[key]
    return None


def _normalize(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value.strip())
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text.casefold() if text else None


def _field_key(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return re.sub(r"[^A-Za-z0-9_]+", "", value).casefold()


def _has_research_marker(title: str) -> bool:
    return title.casefold().startswith(TITLE_MARKER.casefold())


def main() -> int:
    """Read a JSON event from stdin and print the update action as JSON."""

    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
