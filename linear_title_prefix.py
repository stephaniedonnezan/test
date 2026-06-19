"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_CAMEL_CASE_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_NON_WORD = re.compile(r"[^a-z0-9]+")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action for issues moved to to-research.

    The automation runner can pass either the flat Cursor trigger context or a
    nested Linear webhook payload. Non-status changes and non-matching statuses
    intentionally produce no action.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _collect_contexts(event)
    if not _is_status_change_event(contexts):
        return None

    new_status = _find_new_status(contexts)
    if _normalize_text(new_status) != TARGET_STATUS:
        return None

    issue_contexts = _find_issue_contexts(contexts)
    issue_id = _find_issue_id(issue_contexts)
    title = _find_title(issue_contexts)
    if not issue_id or not title:
        return None

    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _collect_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []
    seen: set[int] = set()

    def visit(value: Any) -> None:
        if not isinstance(value, Mapping) or id(value) in seen:
            return

        seen.add(id(value))
        contexts.append(value)

        for key in (
            "triggerContext",
            "payload",
            "data",
            "issue",
            "resource",
            "node",
            "state",
            "workflowState",
        ):
            visit(value.get(key))

    visit(event)
    return contexts


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    context_list = list(contexts)
    if any(_is_direct_status_change(context) for context in context_list):
        return True

    return any(_is_update_event(context) for context in context_list) and any(
        _has_status_change_details(context) for context in context_list
    )


def _is_direct_status_change(context: Mapping[str, Any]) -> bool:
    for key in ("trigger", "webhookType", "event", "type", "action"):
        normalized = _normalize_text(context.get(key))
        compact = normalized.replace(" ", "")
        if compact in {"statuschanged", "statuschange"}:
            return True
        words = set(normalized.split())
        if "status" in words and ({"changed", "change"} & words):
            return True
    return False


def _is_update_event(context: Mapping[str, Any]) -> bool:
    for key in ("trigger", "webhookType", "event", "type", "action"):
        words = set(_normalize_text(context.get(key)).split())
        if {"update", "updated"} & words:
            return True
    return False


def _has_status_change_details(context: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "changedFields"):
        if _fields_include_status(context.get(key)):
            return True

    changes = context.get("changes") or context.get("changed") or context.get("updated")
    if isinstance(changes, Mapping):
        return any(_is_status_field(key) for key in changes)

    return False


def _fields_include_status(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)
    if isinstance(value, Mapping):
        return any(_is_status_field(key) for key in value)
    if isinstance(value, Iterable):
        return any(_fields_include_status(item) for item in value)
    return False


def _is_status_field(value: Any) -> bool:
    normalized = _normalize_text(value)
    compact = normalized.replace(" ", "")
    return compact in {
        "status",
        "statusid",
        "state",
        "stateid",
        "workflowstate",
        "workflowstateid",
    }


def _find_new_status(contexts: Iterable[Mapping[str, Any]]) -> Any:
    context_list = list(contexts)

    for context in context_list:
        status = _status_from_changes(context)
        if status is not None:
            return status

    for context in context_list:
        status = _first_present(
            context,
            (
                "newStatus",
                "new_status",
                "newState",
                "new_state",
                "toStatus",
                "to_status",
                "targetStatus",
                "target_status",
                "statusName",
                "stateName",
            ),
        )
        if status is not None:
            return status

    for context in context_list:
        status = _first_present(
            context,
            ("status", "state", "workflowState", "workflow_state"),
        )
        if status is not None:
            return status

    return None


def _status_from_changes(context: Mapping[str, Any]) -> Any:
    changes = context.get("changes") or context.get("changed") or context.get("updated")
    if not isinstance(changes, Mapping):
        return None

    for field, change in changes.items():
        if _is_status_field(field):
            return _status_from_change(change)

    return None


def _status_from_change(change: Any) -> Any:
    if not isinstance(change, Mapping):
        return change

    for key in ("new", "to", "after", "current", "value"):
        if key in change:
            return _status_from_change(change[key])

    return _first_present(change, ("name", "title", "label"))


def _find_issue_contexts(contexts: Iterable[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    matches = [
        context
        for context in contexts
        if _find_title((context,)) and _find_issue_id((context,))
    ]
    return matches


def _find_issue_id(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        for key in ("issueId", "issue_id", "identifier", "key", "id"):
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _find_title(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        value = context.get("title")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _first_present(context: Mapping[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        if key in context and context[key] is not None:
            return context[key]
    return None


def _has_research_prefix(title: str) -> bool:
    return _normalize_text(title).startswith(PREFIX.lower())


def _normalize_text(value: Any) -> str:
    if isinstance(value, Mapping):
        value = _first_present(value, ("name", "title", "label"))
    if value is None:
        return ""

    text = _CAMEL_CASE_BOUNDARY.sub(" ", str(value))
    text = _NON_WORD.sub(" ", text.lower())
    return " ".join(text.split())


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
