"""Build Linear issue title updates for research status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow state"}


def build_issue_title_update(event: Any) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to research."""
    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_change_event(contexts):
        return None

    new_status = _first_value(contexts, ("newStatus", "new_status", "status"))
    if new_status is None:
        new_status = _first_nested_name(contexts, ("state", "workflowState", "workflow_state"))

    if _normalize_words(new_status) != TARGET_STATUS:
        return None

    issue_id = _clean_string(_first_value(contexts, ("id", "issueId", "issue_id", "identifier")))
    title = _clean_string(_first_value(contexts, ("title", "name")))
    if not issue_id or not title:
        return None

    if title.lower().startswith(TITLE_PREFIX.lower()):
        prefixed_title = title
    else:
        prefixed_title = f"{TITLE_PREFIX}: {title}"

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": prefixed_title,
    }


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return relevant payload layers from most specific metadata to issue data."""
    contexts: list[Mapping[str, Any]] = []

    trigger_context = event.get("triggerContext")
    data = event.get("data")
    issue = data.get("issue") if isinstance(data, Mapping) else None

    for candidate in (event, trigger_context, data, issue):
        if isinstance(candidate, Mapping):
            contexts.append(candidate)

    return contexts


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("trigger", "webhookType", "eventType"):
            normalized = _normalize_words(context.get(key))
            if normalized == "status changed":
                return True

        action = _normalize_words(context.get("action") or context.get("type"))
        if action in {"issue updated", "updated issue", "update"} and _updated_fields_include_status(context):
            return True

    return False


def _updated_fields_include_status(context: Mapping[str, Any]) -> bool:
    updated_fields = context.get("updatedFields") or context.get("updated_fields")
    if updated_fields is None:
        return False

    if isinstance(updated_fields, Mapping):
        fields = updated_fields.keys()
    elif isinstance(updated_fields, (list, tuple, set)):
        fields = updated_fields
    else:
        fields = [updated_fields]

    return any(_normalize_words(field) in STATUS_FIELDS for field in fields)


def _first_value(contexts: list[Mapping[str, Any]], keys: tuple[str, ...]) -> Any:
    for context in contexts:
        for key in keys:
            if key in context and context[key] is not None:
                return context[key]
    return None


def _first_nested_name(contexts: list[Mapping[str, Any]], keys: tuple[str, ...]) -> Any:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if isinstance(value, Mapping):
                name = value.get("name")
                if name is not None:
                    return name
    return None


def _clean_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    cleaned = value.strip()
    return cleaned or None


def _normalize_words(value: Any) -> str:
    if isinstance(value, Mapping):
        value = value.get("name")
    if value is None:
        return ""

    text = str(value)
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        json.dump(update, sys.stdout)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
