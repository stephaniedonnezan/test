"""Build Linear issue title updates for Cursor research automations."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
ACTION = "update_issue_title"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear issue-title update when an issue moves to research."""

    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_change(contexts):
        return None

    new_status = _first_value(
        contexts,
        "newStatus",
        "new_status",
        "toStatus",
        "to_status",
        "status",
        "state",
        "workflowState",
        "workflow_state",
    )
    if _normalize_text(new_status) != TARGET_STATUS:
        return None

    issue_id = _first_value(contexts, "issueId", "issue_id", "identifier", "id")
    title = _first_value(contexts, "title", "name")
    if not isinstance(issue_id, str) or not issue_id.strip():
        return None
    if not isinstance(title, str) or not title.strip():
        return None

    trimmed_title = title.strip()
    if trimmed_title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": ACTION,
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {trimmed_title}",
    }


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Flatten common Linear/Cursor payload nesting in precedence order."""

    contexts: list[Mapping[str, Any]] = []
    for key in ("triggerContext", "data", "issue"):
        value = event.get(key)
        if isinstance(value, Mapping):
            contexts.extend(_contexts(value))

    contexts.append(event)
    return contexts


def _is_status_change(contexts: list[Mapping[str, Any]]) -> bool:
    values = [
        value
        for context in contexts
        for key in ("trigger", "webhookType", "action", "type")
        if (value := context.get(key)) is not None
    ]

    normalized_values = {_normalize_text(value) for value in values}
    if "status changed" in normalized_values:
        return True

    if not normalized_values.intersection({"issue updated", "updated issue", "update"}):
        return False

    updated_fields = [
        field
        for context in contexts
        for key in ("updatedFields", "updated_fields")
        for field in _field_names(context.get(key))
    ]
    return any(_normalize_key(field) in STATUS_FIELDS for field in updated_fields)


def _first_value(contexts: list[Mapping[str, Any]], *keys: str) -> Any:
    for key in keys:
        for context in reversed(contexts):
            value = _get_value(context, key)
            if value is not None:
                return value
    return None


def _get_value(context: Mapping[str, Any], key: str) -> Any:
    value = context.get(key)
    if isinstance(value, Mapping):
        nested_name = value.get("name")
        if nested_name is not None:
            return nested_name
    return value


def _field_names(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, Mapping):
        return [str(key) for key in value]
    if isinstance(value, list):
        return [str(item) for item in value]
    return []


def _normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return re.sub(r"[\s_-]+", " ", spaced).strip().lower()


def _normalize_key(value: Any) -> str:
    return re.sub(r"[\s_-]+", "", _normalize_text(value))


def main() -> int:
    """Read a JSON event from stdin and print the title-update action."""

    event = json.load(sys.stdin)
    action = build_issue_title_update(event)
    if action is not None:
        print(json.dumps(action))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
