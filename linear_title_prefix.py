"""Build Linear issue title updates for issues entering research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"

_STATUS_CHANGE_TRIGGERS = {
    "status changed",
    "status change",
    "statuschanged",
    "state changed",
    "state change",
    "workflow state changed",
}
_ISSUE_UPDATE_TRIGGERS = {
    "issue updated",
    "updated issue",
    "issue update",
    "update",
    "updated",
}
_STATUS_FIELD_NAMES = {"status", "state", "stateid", "workflowstate", "workflowstateid"}
_EXPLICIT_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "newWorkflowState",
    "new_workflow_state",
    "statusName",
    "status_name",
    "stateName",
    "state_name",
    "workflowStateName",
    "workflow_state_name",
)
_NESTED_STATUS_KEYS = ("status", "state", "workflowState")
_ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "id")
_CHILD_CONTEXT_KEYS = ("triggerContext", "payload", "data", "issue", "node", "object")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue-title update action when a Linear issue enters research."""

    if not isinstance(event, Mapping):
        return None

    contexts = list(_candidate_contexts(event))
    if not _is_status_change_event(contexts):
        return None

    new_status = _extract_new_status(contexts)
    if _normalize(new_status) != RESEARCH_STATUS:
        return None

    title_context, title = _extract_title_context(contexts)
    issue_id = _extract_issue_id(contexts, preferred_context=title_context)
    if not title or not issue_id:
        return None

    title = title.strip()
    if not title or title.casefold().startswith(PREFIX.casefold()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _candidate_contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely event/issue contexts without descending into unrelated objects."""

    seen: set[int] = set()
    queue: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and id(value) not in seen:
            seen.add(id(value))
            queue.append(value)

    for key in ("triggerContext", "payload", "data", "issue"):
        add(event.get(key))
    add(event)

    index = 0
    while index < len(queue):
        current = queue[index]
        index += 1
        yield current

        for key in _CHILD_CONTEXT_KEYS:
            add(current.get(key))


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    saw_issue_update = False

    for context in contexts:
        for key in ("trigger", "webhookType", "action", "type", "eventType"):
            value = context.get(key)
            normalized = _normalize(value)
            compact = normalized.replace(" ", "")
            if normalized in _STATUS_CHANGE_TRIGGERS or compact in _STATUS_CHANGE_TRIGGERS:
                return True
            if normalized in _ISSUE_UPDATE_TRIGGERS:
                saw_issue_update = True

        if saw_issue_update and _updated_status_fields(context):
            return True

    return False


def _updated_status_fields(context: Mapping[str, Any]) -> bool:
    fields = context.get("updatedFields") or context.get("updated_fields")
    if isinstance(fields, str):
        field_names = [fields]
    elif isinstance(fields, Iterable) and not isinstance(fields, (Mapping, bytes)):
        field_names = [str(field) for field in fields]
    else:
        field_names = []

    for field in field_names:
        if _normalize_field_name(field) in _STATUS_FIELD_NAMES:
            return True

    for key in ("updatedFrom", "updated_from", "previousValues", "previous_values"):
        previous = context.get(key)
        if isinstance(previous, Mapping):
            for field in previous:
                if _normalize_field_name(str(field)) in _STATUS_FIELD_NAMES:
                    return True

    return False


def _extract_new_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    contexts = list(contexts)

    for context in contexts:
        for key in _EXPLICIT_STATUS_KEYS:
            status = _string_value(context.get(key))
            if status:
                return status

    for context in contexts:
        for key in _NESTED_STATUS_KEYS:
            status = _status_value(context.get(key))
            if status:
                return status

    return None


def _extract_title_context(
    contexts: Iterable[Mapping[str, Any]],
) -> tuple[Mapping[str, Any] | None, str | None]:
    for context in contexts:
        title = _string_value(context.get("title"))
        if title:
            return context, title
    return None, None


def _extract_issue_id(
    contexts: Iterable[Mapping[str, Any]],
    *,
    preferred_context: Mapping[str, Any] | None,
) -> str | None:
    ordered_contexts: list[Mapping[str, Any]] = []
    if preferred_context is not None:
        ordered_contexts.append(preferred_context)
    ordered_contexts.extend(context for context in contexts if context is not preferred_context)

    for context in ordered_contexts:
        for key in _ISSUE_ID_KEYS:
            issue_id = _string_value(context.get(key))
            if issue_id:
                return issue_id
    return None


def _status_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            status = _string_value(value.get(key))
            if status:
                return status
    return _string_value(value)


def _string_value(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _normalize(value: Any) -> str:
    text = _string_value(value)
    if not text:
        return ""
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.casefold().split())


def _normalize_field_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", _normalize(value))


def main() -> int:
    event = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(event)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
