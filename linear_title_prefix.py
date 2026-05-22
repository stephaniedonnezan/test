"""Build safe Linear issue-title updates for research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = ("status", "state", "workflowState", "workflow_status", "workflowStatus")
EXPLICIT_NEW_STATUS_FIELDS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "newWorkflowState",
    "new_workflow_state",
)
TRIGGER_FIELDS = ("trigger", "webhookType", "action", "type", "event", "eventType")
UPDATED_FIELDS_KEYS = (
    "updatedFields",
    "updated_fields",
    "changedFields",
    "changed_fields",
    "updatedFieldNames",
    "updated_field_names",
)
STATUS_FIELD_NAMES = {"status", "state", "workflow state", "workflow status"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to to research.

    The function is intentionally side-effect free: callers can decide how to
    execute the returned update action against Linear.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _collect_contexts(event)
    if not _is_status_change_event(contexts):
        return None

    status = _extract_new_status(contexts)
    if _normalize_label(status) != TARGET_STATUS:
        return None

    issue = _find_issue_context(contexts)
    issue_id = _extract_text(issue, ("id", "issueId", "issue_id", "identifier"))
    title = _extract_text(issue, ("title", "name"))
    if not issue_id or not title:
        return None

    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _collect_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Collect likely metadata and issue dictionaries in precedence order."""

    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in contexts:
            contexts.append(value)

    add(event)

    for key in ("triggerContext", "context", "payload", "data", "issue"):
        value = event.get(key)
        add(value)
        if isinstance(value, Mapping):
            for nested_key in ("triggerContext", "context", "payload", "data", "issue"):
                add(value.get(nested_key))

    for context in list(contexts):
        for key in ("issue", "data"):
            value = context.get(key)
            add(value)
            if isinstance(value, Mapping):
                add(value.get("issue"))

    return contexts


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    saw_status_changed_trigger = False
    saw_issue_update_trigger = False

    for context in contexts:
        for field in TRIGGER_FIELDS:
            trigger = _normalize_label(context.get(field))
            if trigger == "status changed":
                saw_status_changed_trigger = True
            if trigger in {"issue updated", "updated issue", "update", "updated"}:
                saw_issue_update_trigger = True

    if saw_status_changed_trigger:
        return True

    return saw_issue_update_trigger and any(
        _updated_fields_include_status(context) for context in contexts
    )


def _updated_fields_include_status(context: Mapping[str, Any]) -> bool:
    for key in UPDATED_FIELDS_KEYS:
        updated_fields = context.get(key)
        if updated_fields is None:
            continue

        if isinstance(updated_fields, Mapping):
            values = list(updated_fields.keys())
        elif isinstance(updated_fields, str):
            values = [updated_fields]
        elif isinstance(updated_fields, Iterable):
            values = list(updated_fields)
        else:
            values = [updated_fields]

        for value in values:
            if _normalize_label(value) in STATUS_FIELD_NAMES:
                return True

    return False


def _extract_new_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        for field in EXPLICIT_NEW_STATUS_FIELDS:
            value = _extract_status_value(context.get(field))
            if value:
                return value

    for context in contexts:
        for field in STATUS_FIELDS:
            value = _extract_status_value(context.get(field))
            if value:
                return value

    return None


def _extract_status_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("name", "title", "status", "state"):
            text = _to_text(value.get(key))
            if text:
                return text
        return None

    return _to_text(value)


def _find_issue_context(contexts: Iterable[Mapping[str, Any]]) -> Mapping[str, Any]:
    for context in contexts:
        issue = context.get("issue")
        if isinstance(issue, Mapping) and _extract_text(issue, ("title", "name")):
            return issue

    for context in contexts:
        if _extract_text(context, ("title", "name")):
            return context

    return {}


def _extract_text(context: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for key in keys:
        text = _to_text(context.get(key))
        if text:
            return text
    return None


def _to_text(value: Any) -> str | None:
    if value is None or isinstance(value, (Mapping, list, tuple, set)):
        return None

    text = str(value).strip()
    return text or None


def _has_research_prefix(title: str) -> bool:
    return title.strip().lower().startswith(TITLE_PREFIX.lower())


def _normalize_label(value: Any) -> str:
    text = _extract_status_value(value) or ""
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def main() -> int:
    payload = json.load(sys.stdin)
    result = build_issue_title_update(payload)
    if result is not None:
        print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
