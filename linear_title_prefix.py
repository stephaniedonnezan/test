"""Build title updates for Linear issues entering the research status."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


RESEARCH_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow state"}
STATUS_CHANGE_TRIGGERS = {"status changed", "status change", "status updated"}
ISSUE_UPDATE_TRIGGERS = {"issue updated", "updated issue", "update", "updated"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to To Research."""
    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_change_event(contexts):
        return None

    status = _first_text(
        contexts,
        (
            "newStatus",
            "new_status",
            "newState",
            "new_state",
            "newWorkflowState",
            "new_workflow_state",
            "status",
            "state.name",
            "workflowState.name",
            "workflow_state.name",
        ),
    )
    if _normalize(status) != TARGET_STATUS:
        return None

    issue_id = _first_text(
        contexts,
        ("id", "issueId", "issue_id", "identifier", "issue.id", "issue.identifier"),
    )
    title = _first_text(contexts, ("title", "name", "issue.title", "issue.name"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{RESEARCH_PREFIX}: {title}",
    }


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []
    _collect_contexts(event, contexts)
    return contexts


def _collect_contexts(value: Any, contexts: list[Mapping[str, Any]]) -> None:
    if not isinstance(value, Mapping):
        return

    contexts.append(value)
    for key in ("triggerContext", "data", "payload", "issue"):
        nested = value.get(key)
        if isinstance(nested, Mapping) and nested not in contexts:
            _collect_contexts(nested, contexts)


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("trigger", "event", "action", "type", "webhookType"):
            normalized = _normalize(context.get(key))
            if normalized in STATUS_CHANGE_TRIGGERS:
                return True
            if normalized in ISSUE_UPDATE_TRIGGERS:
                return _updated_fields_include_status(contexts)

    return False


def _updated_fields_include_status(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        value = context.get("updatedFields", context.get("updated_fields"))
        if isinstance(value, str):
            fields = [value]
        elif isinstance(value, (list, tuple, set)):
            fields = list(value)
        elif isinstance(value, Mapping):
            fields = list(value.keys())
        else:
            continue

        for field in fields:
            if _normalize(field) in STATUS_FIELDS:
                return True

    return False


def _first_text(contexts: list[Mapping[str, Any]], paths: tuple[str, ...]) -> str | None:
    for path in paths:
        for context in contexts:
            value = _get_path(context, path)
            if isinstance(value, Mapping):
                value = value.get("name") or value.get("title")
            if value is None:
                continue
            text = str(value).strip()
            if text:
                return text
    return None


def _get_path(context: Mapping[str, Any], path: str) -> Any:
    value: Any = context
    for part in path.split("."):
        if not isinstance(value, Mapping) or part not in value:
            return None
        value = value[part]
    return value


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(RESEARCH_PREFIX.lower())


def _normalize(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def main() -> int:
    """Read an event JSON object from stdin and print a title update if needed."""
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    update = build_issue_title_update(event)
    if update:
        print(json.dumps(update))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
