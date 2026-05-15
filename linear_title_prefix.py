"""Build Linear issue title updates for issues entering research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow_state"}
TRIGGER_KEYS = ("trigger", "action", "type", "webhookType")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return the issue-title update action for a matching Linear event.

    The automation payload can arrive either as Cursor's flat trigger context or
    as a nested Linear webhook. This function is intentionally pure so callers
    can decide how to apply the returned action.
    """
    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not _is_status_change(contexts):
        return None

    explicit_new_status = _first_value(contexts, ("newStatus", "new_status"))
    if explicit_new_status is not None:
        if _normalize_status(explicit_new_status) != TARGET_STATUS:
            return None
    elif _status_from_contexts(contexts) != TARGET_STATUS:
        return None

    issue_id = _clean_string(_first_value(contexts, ("issueId", "issue_id", "id", "identifier")))
    title = _clean_string(_first_value(contexts, ("title", "name")))

    if not issue_id or not title:
        return None

    if title.lower().startswith(PREFIX.lower()):
        new_title = title
    else:
        new_title = f"{PREFIX}: {title}"

    return {"action": "update_issue_title", "issueId": issue_id, "title": new_title}


handle_issue_status_changed = build_issue_title_update


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping):
            contexts.append(value)

    add(event)
    add(event.get("triggerContext"))
    add(event.get("issue"))

    data = event.get("data")
    add(data)
    if isinstance(data, Mapping):
        add(data.get("issue"))

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        add(trigger_context.get("issue"))
        nested_data = trigger_context.get("data")
        add(nested_data)
        if isinstance(nested_data, Mapping):
            add(nested_data.get("issue"))

    return contexts


def _is_status_change(contexts: Iterable[Mapping[str, Any]]) -> bool:
    saw_issue_update = False
    saw_status_field = False

    for context in contexts:
        for key in TRIGGER_KEYS:
            value = context.get(key)
            if not isinstance(value, str):
                continue

            normalized = _normalize_phrase(value)
            compact = normalized.replace(" ", "")

            if normalized in {"status changed", "status change"} or compact == "statuschanged":
                return True
            if normalized in {"issue updated", "updated issue"}:
                saw_issue_update = True
            if normalized == "update" and _is_issue_context(context):
                saw_issue_update = True

        for field_key in ("updatedFields", "changedFields", "updated_fields", "changes"):
            if _contains_status_field(context.get(field_key)):
                saw_status_field = True

        if _contains_status_field(context.get("updatedFrom")):
            saw_status_field = True

    return saw_issue_update and saw_status_field


def _is_issue_context(context: Mapping[str, Any]) -> bool:
    return any(_normalize_phrase(context.get(key)) == "issue" for key in ("webhookType", "type"))


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        normalized = _normalize_field_name(value)
        return normalized in STATUS_FIELDS or normalized.endswith("status") or normalized.endswith("state")

    if isinstance(value, Mapping):
        return any(_contains_status_field(key) for key in value)

    if isinstance(value, Iterable):
        return any(_contains_status_field(item) for item in value)

    return False


def _status_from_contexts(contexts: Iterable[Mapping[str, Any]]) -> str:
    direct_status = _normalize_status(_first_value(contexts, ("status",)))
    if direct_status:
        return direct_status

    for context in contexts:
        for key in ("state", "workflowState", "workflow_state"):
            value = context.get(key)
            if isinstance(value, Mapping):
                status = _normalize_status(value.get("name"))
                if status:
                    return status
            else:
                status = _normalize_status(value)
                if status:
                    return status

    return ""


def _first_value(contexts: Iterable[Mapping[str, Any]], keys: tuple[str, ...]) -> Any:
    for context in contexts:
        for key in keys:
            if key in context:
                value = context[key]
                if value is not None:
                    return value
    return None


def _normalize_status(value: Any) -> str:
    return _normalize_phrase(value)


def _normalize_field_name(value: Any) -> str:
    return _normalize_phrase(value).replace(" ", "")


def _normalize_phrase(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    split_camel_case = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    words_only = re.sub(r"[^A-Za-z0-9]+", " ", split_camel_case)
    return " ".join(words_only.strip().lower().split())


def _clean_string(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


def main() -> int:
    """Read an event from stdin and write the update action as JSON."""
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    result = build_issue_title_update(payload)
    if result is not None:
        print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
