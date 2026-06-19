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

_CAMEL_CASE_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_NON_ALNUM = re.compile(r"[^A-Za-z0-9]+")

_DIRECT_STATUS_CHANGE_EVENTS = {
    "status changed",
    "status change",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
    "issue status changed",
    "issue status change",
    "issue state changed",
    "issue state change",
}

_GENERIC_UPDATE_EVENTS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}

_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "state id",
    "state name",
    "workflow state",
    "workflow state id",
    "workflow state name",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return an issue-title update action when a Linear issue moves to research.

    The function accepts both the flat Cursor automation trigger context and
    common nested Linear webhook shapes.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = list(_iter_contexts(event))

    if not _is_status_change_event(contexts):
        return None

    if _normalize(_new_status(contexts)) != TARGET_STATUS:
        return None

    issue_id = _first_text(contexts, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_text(contexts, ("title", "name"))

    if not issue_id or not title:
        return None

    trimmed_title = title.strip()
    if _has_research_prefix(trimmed_title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {trimmed_title}",
    }


def _iter_contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield useful event dictionaries from outermost to innermost."""

    seen: set[int] = set()
    queue: list[Mapping[str, Any]] = [event]

    while queue:
        context = queue.pop(0)
        context_id = id(context)
        if context_id in seen:
            continue
        seen.add(context_id)
        yield context

        for key in (
            "automation_trigger_info",
            "automationTriggerInfo",
            "triggerContext",
            "trigger_context",
            "webhook",
            "data",
            "issue",
            "node",
        ):
            child = context.get(key)
            if isinstance(child, Mapping):
                queue.append(child)


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("trigger", "webhookType", "webhook_type", "action", "type"):
            event_name = _normalize(context.get(key))
            if event_name in _DIRECT_STATUS_CHANGE_EVENTS:
                return True
            if event_name in _GENERIC_UPDATE_EVENTS and _updated_fields_include_status(
                contexts
            ):
                return True

    return False


def _updated_fields_include_status(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in (
            "updatedFields",
            "updated_fields",
            "changedFields",
            "changed_fields",
            "changes",
            "updatedFrom",
            "updated_from",
        ):
            if _contains_status_field(context.get(key)):
                return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize(value) in _STATUS_FIELD_NAMES

    if isinstance(value, Mapping):
        return any(_contains_status_field(key) for key in value.keys())

    if isinstance(value, Iterable):
        return any(_contains_status_field(item) for item in value)

    return False


def _new_status(contexts: list[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        explicit_status = _first_text(
            [context],
            (
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
            ),
        )
        if explicit_status:
            return explicit_status

    for context in contexts:
        status = _first_text([context], ("status", "state", "workflowState"))
        if status:
            return status

    return None


def _first_text(contexts: Iterable[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            text = _coerce_text(value)
            if text:
                return text

    return None


def _coerce_text(value: Any) -> str | None:
    if isinstance(value, str):
        text = value.strip()
        return text or None

    if isinstance(value, Mapping):
        return _first_text([value], ("name", "title", "identifier", "key", "id"))

    return None


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())


def _normalize(value: Any) -> str:
    text = _coerce_text(value)
    if text is None:
        return ""

    split_camel = _CAMEL_CASE_BOUNDARY.sub(" ", text)
    normalized = _NON_ALNUM.sub(" ", split_camel).casefold()
    return " ".join(normalized.split())


def main() -> int:
    event = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(event), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
