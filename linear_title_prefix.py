"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = frozenset({"status", "state", "workflowstate", "workflow_status"})


def build_issue_title_update(event: Any) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to To Research."""
    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_change_event(contexts):
        return None

    new_status = _first_value(contexts, "newStatus", "new_status", "status")
    if _normalized_status(new_status) != TARGET_STATUS:
        status_name = _first_nested_name(contexts, "state", "workflowState", "workflow_status")
        if _normalized_status(status_name) != TARGET_STATUS:
            return None

    issue_id = _clean_string(_first_value(contexts, "issueId", "issue_id", "id", "identifier"))
    title = _clean_string(_first_value(contexts, "title", "name"))
    if not issue_id or not title:
        return None

    if _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []

    def visit(value: Any) -> None:
        if not isinstance(value, Mapping):
            return

        contexts.append(value)
        for key in ("triggerContext", "data", "issue", "state", "workflowState", "workflow_status"):
            nested = value.get(key)
            if isinstance(nested, Mapping):
                visit(nested)

    visit(event)
    return contexts


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    event_markers = _all_values(contexts, "trigger", "webhookType", "action", "type")
    if any(_normalize(marker) in {"status changed", "status change", "issue status changed"} for marker in event_markers):
        return True

    update_markers = {"issue updated", "updated issue", "update", "updated"}
    if any(_normalize(marker) in update_markers for marker in event_markers):
        return _updated_fields_include_status(contexts)

    return False


def _updated_fields_include_status(contexts: list[Mapping[str, Any]]) -> bool:
    for value in _all_values(contexts, "updatedFields", "updated_fields", "changedFields", "changed_fields"):
        fields: list[Any]
        if isinstance(value, str):
            fields = re.split(r"[, ]+", value)
        elif isinstance(value, Mapping):
            fields = list(value)
        elif isinstance(value, list | tuple | set):
            fields = list(value)
        else:
            continue

        if any(_normalize_field(field) in STATUS_FIELDS for field in fields):
            return True
    return False


def _first_value(contexts: list[Mapping[str, Any]], *keys: str) -> Any:
    for context in contexts:
        for key in keys:
            if key in context:
                return context[key]
    return None


def _all_values(contexts: list[Mapping[str, Any]], *keys: str) -> list[Any]:
    values: list[Any] = []
    for context in contexts:
        for key in keys:
            if key in context:
                values.append(context[key])
    return values


def _first_nested_name(contexts: list[Mapping[str, Any]], *keys: str) -> Any:
    for context in contexts:
        for key in keys:
            nested = context.get(key)
            if isinstance(nested, Mapping) and "name" in nested:
                return nested["name"]
    return None


def _clean_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    stripped = value.strip()
    return stripped or None


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def _normalized_status(value: Any) -> str | None:
    normalized = _normalize(value)
    return normalized or None


def _normalize(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    spaced = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", value)
    words = re.sub(r"[^A-Za-z0-9]+", " ", spaced).strip().lower()
    return re.sub(r"\s+", " ", words)


def _normalize_field(value: Any) -> str:
    return _normalize(value).replace(" ", "")


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON input: {exc}", file=sys.stderr)
        return 1

    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
