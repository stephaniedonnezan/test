"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when an issue moves to To Research.

    The function is intentionally side-effect free: callers can pass a Linear or
    Cursor automation payload and decide how to apply the returned action.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_change_event(contexts):
        return None

    if _normalize_words(_new_status(contexts)) != TARGET_STATUS:
        return None

    issue_id = _trimmed_string(_first_value(contexts, ("issueId", "issue_id", "identifier", "key", "id")))
    title = _trimmed_string(_first_value(contexts, ("title", "name")))
    if not issue_id or not title or _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)

    data = event.get("data")
    add(event.get("triggerContext"))
    if isinstance(data, Mapping):
        add(data.get("issue"))
    add(event.get("issue"))
    if isinstance(data, Mapping):
        add(data)
    add(event)

    for context in list(contexts):
        add(context.get("state"))
        add(context.get("workflowState"))
        add(context.get("status"))

    return contexts


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    event_names = [
        _normalize_words(context.get(key))
        for context in contexts
        for key in ("trigger", "webhookType", "action", "type")
    ]

    if any(name in {"status changed", "status change", "state changed", "workflow state changed"} for name in event_names):
        return True

    if any(name in {"update", "updated", "issue update", "issue updated", "updated issue"} for name in event_names):
        return _changed_fields_include_status(contexts)

    return False


def _changed_fields_include_status(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        changed_values = [
            context.get("updatedFields"),
            context.get("updated_fields"),
            context.get("changedFields"),
            context.get("changed_fields"),
            context.get("changes"),
        ]
        for value in changed_values:
            if _value_mentions_status_field(value):
                return True
    return False


def _value_mentions_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field_name(value)

    if isinstance(value, Mapping):
        return any(_is_status_field_name(key) for key in value.keys())

    if isinstance(value, (list, tuple, set)):
        return any(_value_mentions_status_field(item) for item in value)

    return False


def _is_status_field_name(value: Any) -> bool:
    normalized = _normalize_words(value)
    return normalized in {"status", "state", "workflow state", "workflow status"}


def _new_status(contexts: list[Mapping[str, Any]]) -> Any:
    explicit_status = _first_value(
        contexts,
        (
            "newStatus",
            "new_status",
            "newState",
            "new_state",
            "statusName",
            "status_name",
            "stateName",
            "state_name",
            "workflowStateName",
            "workflow_state_name",
        ),
    )
    if explicit_status is not None:
        return explicit_status

    for context in contexts:
        for key in ("status", "state", "workflowState"):
            value = context.get(key)
            if isinstance(value, Mapping):
                name = value.get("name") or value.get("title")
                if name is not None:
                    return name
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


def _trimmed_string(value: Any) -> str | None:
    if isinstance(value, str):
        trimmed = value.strip()
        return trimmed or None
    return None


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(TITLE_PREFIX.casefold())


def _normalize_words(value: Any) -> str:
    if value is None:
        return ""

    text = str(value)
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.casefold().split())


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON payload: {exc}", file=sys.stderr)
        return 1

    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
