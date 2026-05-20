"""Build title update actions for Linear issues moved to research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to To Research."""
    if not isinstance(event, Mapping):
        return None

    contexts = _collect_contexts(event)
    if not _is_status_change_event(contexts):
        return None

    if _normalize_status(_extract_status(contexts)) != _normalize_status(TARGET_STATUS):
        return None

    issue_id = _clean_string(_first_value(contexts, ("id", "issueId", "issue_id", "identifier")))
    title = _clean_string(_first_value(contexts, ("title",)))
    if not issue_id or not title or _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _collect_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)

    add(event)
    for key in ("triggerContext", "trigger_context", "payload", "webhook"):
        add(event.get(key))

    data = event.get("data")
    add(data)
    if isinstance(data, Mapping):
        for key in ("issue", "node"):
            add(data.get(key))

    issue = event.get("issue")
    add(issue)

    return contexts


def _is_status_change_event(contexts: Sequence[Mapping[str, Any]]) -> bool:
    trigger_values: list[str] = []
    for context in contexts:
        for key in ("trigger", "webhookType", "webhook_type", "action", "type"):
            value = context.get(key)
            if isinstance(value, str):
                trigger_values.append(value)

    normalized_triggers = {_normalize_token(value) for value in trigger_values}
    if normalized_triggers & {"statuschanged", "statuschange", "statechanged", "workflowstatechanged"}:
        return True

    if normalized_triggers & {"issueupdated", "updatedissue", "update", "updated"}:
        return _updated_fields_include_status(contexts)

    return False


def _updated_fields_include_status(contexts: Sequence[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            fields = context.get(key)
            if isinstance(fields, str) and _normalize_token(fields) in STATUS_FIELDS:
                return True
            if isinstance(fields, Sequence) and not isinstance(fields, (str, bytes, bytearray)):
                for field in fields:
                    if isinstance(field, str) and _normalize_token(field) in STATUS_FIELDS:
                        return True

        changed = context.get("updatedFrom") or context.get("updated_from") or context.get("changes")
        if isinstance(changed, Mapping):
            for field in changed:
                if isinstance(field, str) and _normalize_token(field) in STATUS_FIELDS:
                    return True

    return False


def _extract_status(contexts: Sequence[Mapping[str, Any]]) -> Any:
    for key in ("newStatus", "new_status", "statusName", "status_name", "newState", "new_state"):
        value = _first_value(contexts, (key,))
        if value is not None:
            return value

    for context in contexts:
        for key in ("state", "workflowState", "workflow_state", "status"):
            value = context.get(key)
            if isinstance(value, Mapping):
                name = value.get("name") or value.get("title")
                if name is not None:
                    return name
            elif value is not None:
                return value

    return None


def _first_value(contexts: Sequence[Mapping[str, Any]], keys: Sequence[str]) -> Any:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if value is not None:
                return value
    return None


def _clean_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def _normalize_status(value: Any) -> str | None:
    text = _clean_string(value)
    if text is None:
        return None
    words = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    words = re.sub(r"[^a-zA-Z0-9]+", " ", words).strip().lower()
    return " ".join(words.split())


def _normalize_token(value: str) -> str:
    normalized = _normalize_status(value)
    return "" if normalized is None else normalized.replace(" ", "")


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
