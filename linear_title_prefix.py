"""Build Linear issue title update actions for research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to To Research."""
    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_change_event(contexts):
        return None

    status = _destination_status(contexts)
    if _normalize(status) != TARGET_STATUS:
        return None

    issue_id = _first_text(contexts, ("id", "issueId", "issue_id", "identifier"))
    title = _first_text(contexts, ("title",))
    if not issue_id or not title:
        return None

    if title.casefold().startswith(PREFIX.casefold()):
        new_title = title
    else:
        new_title = f"{PREFIX}: {title}"

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": new_title,
    }


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping):
            contexts.append(value)

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        add(trigger_context)
        for key in ("data", "issue"):
            add(trigger_context.get(key))

    data = event.get("data")
    if isinstance(data, Mapping):
        add(data)
        add(data.get("issue"))

    add(event.get("issue"))
    add(event)

    return contexts


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("trigger", "webhookType", "action", "type"):
            value = context.get(key)
            normalized = _normalize(value)
            if normalized in {"status changed", "status change"}:
                return True
            if normalized in {"issue updated", "updated issue", "update", "updated"}:
                return _updated_status_field(contexts)
    return False


def _updated_status_field(contexts: Iterable[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            fields = context.get(key)
            if isinstance(fields, str):
                fields = [fields]
            if not isinstance(fields, Iterable):
                continue
            for field in fields:
                normalized = _normalize(field).replace(" ", "")
                if normalized in STATUS_FIELDS:
                    return True
    return False


def _destination_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    for key in ("newStatus", "new_status", "statusName", "status_name"):
        value = _first_text(contexts, (key,))
        if value:
            return value

    for context in contexts:
        for key in ("status", "state", "workflowState", "workflow_state"):
            value = context.get(key)
            if isinstance(value, Mapping):
                name = _text(value.get("name"))
                if name:
                    return name
            else:
                text = _text(value)
                if text:
                    return text
    return None


def _first_text(contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for context in contexts:
        for key in keys:
            value = _text(context.get(key))
            if value:
                return value
    return None


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize(value: Any) -> str:
    text = _text(value)
    if not text:
        return ""
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.casefold().split())


def main() -> int:
    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
