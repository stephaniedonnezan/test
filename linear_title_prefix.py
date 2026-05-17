"""Build Linear issue title updates for research status changes.

The automation runtime can pass either a flat trigger context or a nested
Linear webhook payload.  This module keeps the decision pure and side-effect
free so the runtime can apply the returned action.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow state"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue-title update action when the event enters research."""

    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_change_event(contexts):
        return None

    if _normalized_status(_first_status_value(contexts)) != RESEARCH_STATUS:
        return None

    issue_id = _clean_string(_first_value(contexts, ("id", "issueId", "issue_id", "identifier")))
    title = _clean_string(_first_value(contexts, ("title", "name")))
    if not issue_id or not title:
        return None

    if title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return likely metadata/issue mappings from outermost to innermost."""

    contexts: list[Mapping[str, Any]] = []

    def visit(value: Any) -> None:
        if not isinstance(value, Mapping) or value in contexts:
            return

        contexts.append(value)
        for key in ("triggerContext", "webhook", "payload", "data", "issue"):
            nested = value.get(key)
            if isinstance(nested, Mapping):
                visit(nested)

    visit(event)
    return contexts


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    trigger_values = []
    for context in contexts:
        for key in ("trigger", "webhookType", "action", "type"):
            value = context.get(key)
            if isinstance(value, str):
                trigger_values.append(value)

    if any(_normalize_text(value) == "status changed" for value in trigger_values):
        return True

    updated_fields = _updated_fields(contexts)
    if updated_fields and not (updated_fields & STATUS_FIELDS):
        return False

    # Linear issue webhooks commonly send action=update for field changes.
    return any(_normalize_text(value) in {"update", "updated", "issue updated", "updated issue"} for value in trigger_values)


def _updated_fields(contexts: list[Mapping[str, Any]]) -> set[str]:
    fields: set[str] = set()
    for context in contexts:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            value = context.get(key)
            if isinstance(value, str):
                fields.add(_normalize_field(value))
            elif isinstance(value, (list, tuple, set)):
                fields.update(_normalize_field(item) for item in value if isinstance(item, str))

        updated_from = context.get("updatedFrom")
        if isinstance(updated_from, Mapping):
            fields.update(_normalize_field(key) for key in updated_from.keys() if isinstance(key, str))

    return fields


def _first_status_value(contexts: list[Mapping[str, Any]]) -> Any:
    for key in ("newStatus", "new_status", "statusName", "status_name"):
        value = _first_value(contexts, (key,))
        if value is not None:
            return value

    for context in contexts:
        for key in ("status", "state", "workflowState", "workflow_state"):
            value = context.get(key)
            if isinstance(value, Mapping):
                nested_name = value.get("name")
                if nested_name is not None:
                    return nested_name
            elif value is not None:
                return value

    return None


def _first_value(contexts: list[Mapping[str, Any]], keys: tuple[str, ...]) -> Any:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if value is not None:
                return value
    return None


def _clean_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    stripped = value.strip()
    return stripped or None


def _normalized_status(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return _normalize_text(value)


def _normalize_field(value: str) -> str:
    normalized = _normalize_text(value)
    if normalized.endswith(" id"):
        normalized = normalized.removesuffix(" id")
    return normalized


def _normalize_text(value: str) -> str:
    separated = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    normalized = re.sub(r"[^A-Za-z0-9]+", " ", separated).strip().lower()
    return re.sub(r"\s+", " ", normalized)


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(json.dumps({"error": f"invalid JSON: {exc}"}), file=sys.stderr)
        return 1

    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
