"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

STATUS_FIELD_NAMES = {"status", "state", "workflow state", "workflowstate"}
DIRECT_STATUS_CHANGE_EVENTS = {
    "status changed",
    "status change",
    "statuschanged",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
}
GENERIC_UPDATE_EVENTS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to To Research.

    The automation payloads can be flat Cursor trigger contexts or nested Linear
    webhook payloads. This function is intentionally side-effect free so the
    runner can decide how to apply the returned update action.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _collect_contexts(event)
    if not _is_status_change_event(contexts):
        return None

    new_status = _extract_new_status(contexts)
    if _normalize_label(new_status) != TARGET_STATUS:
        return None

    issue_id = _extract_first_text(contexts, ("id", "issueId", "issue_id", "identifier", "key"))
    title = _extract_first_text(contexts, ("title", "name"))
    if not issue_id or not title:
        return None

    clean_title = title.strip()
    if not clean_title or _has_research_prefix(clean_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {clean_title}",
    }


def _collect_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Collect useful payload scopes, preferring outer automation metadata."""

    contexts: list[Mapping[str, Any]] = [event]
    for key in ("triggerContext", "trigger_context", "webhook", "payload", "data", "issue"):
        value = event.get(key)
        if isinstance(value, Mapping):
            contexts.extend(_collect_nested_contexts(value))
    return contexts


def _collect_nested_contexts(mapping: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = [mapping]
    for key in ("triggerContext", "trigger_context", "data", "issue", "state", "workflowState"):
        value = mapping.get(key)
        if isinstance(value, Mapping):
            contexts.append(value)
    return contexts


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    saw_generic_update = False
    context_list = list(contexts)

    for context in context_list:
        for key in ("trigger", "action", "type", "webhookType", "webhook_type"):
            label = _normalize_label(_extract_status_text(context.get(key)))
            if label in DIRECT_STATUS_CHANGE_EVENTS:
                return True
            if label in GENERIC_UPDATE_EVENTS:
                saw_generic_update = True

    return saw_generic_update and _has_status_change_signal(context_list)


def _has_status_change_signal(contexts: Iterable[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            fields = context.get(key)
            if _contains_status_field(fields):
                return True

        for key in ("changes", "changed", "updated"):
            changes = context.get(key)
            if isinstance(changes, Mapping):
                if any(_normalize_label(str(field)) in STATUS_FIELD_NAMES for field in changes):
                    return True
            elif _contains_status_field(changes):
                return True

        if any(_normalize_key(key) in _new_status_key_names() for key in context):
            return True

    return False


def _extract_new_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    context_list = list(contexts)
    for context in context_list:
        for key, value in context.items():
            if _normalize_key(key) in _new_status_key_names():
                status = _extract_status_text(value)
                if status:
                    return status

    for context in context_list:
        for changes_key in ("changes", "changed", "updated"):
            changes = context.get(changes_key)
            if not isinstance(changes, Mapping):
                continue
            for field_name, change in changes.items():
                if _normalize_label(str(field_name)) not in STATUS_FIELD_NAMES:
                    continue
                status = _extract_changed_status_text(change)
                if status:
                    return status

    for context in context_list:
        for key, value in context.items():
            if _normalize_key(key) in {"status", "state", "workflowstate", "workflow state"}:
                status = _extract_status_text(value)
                if status:
                    return status

    return None


def _extract_first_text(contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    normalized_keys = {_normalize_key(key) for key in keys}
    for context in contexts:
        for key, value in context.items():
            if _normalize_key(key) in normalized_keys:
                text = _extract_status_text(value)
                if text:
                    return text
    return None


def _extract_changed_status_text(change: Any) -> str | None:
    if isinstance(change, Mapping):
        for key in ("to", "new", "newValue", "new_value", "after", "current", "value", "name"):
            status = _extract_status_text(change.get(key))
            if status:
                return status
    return _extract_status_text(change)


def _extract_status_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        for key in ("name", "title", "status", "state", "workflowState", "identifier", "key"):
            text = _extract_status_text(value.get(key))
            if text:
                return text
    return None


def _contains_status_field(fields: Any) -> bool:
    if isinstance(fields, str):
        return _normalize_label(fields) in STATUS_FIELD_NAMES
    if isinstance(fields, Mapping):
        return any(_normalize_label(str(key)) in STATUS_FIELD_NAMES for key in fields)
    if isinstance(fields, Iterable):
        return any(_contains_status_field(field) for field in fields)
    return False


def _new_status_key_names() -> set[str]:
    return {
        "newstatus",
        "new status",
        "newstate",
        "new state",
        "newworkflowstate",
        "new workflow state",
        "statusname",
        "status name",
        "statename",
        "state name",
        "workflowstatename",
        "workflow state name",
    }


def _has_research_prefix(title: str) -> bool:
    return re.match(rf"^\s*{re.escape(PREFIX)}\b", title, flags=re.IGNORECASE) is not None


def _normalize_key(value: Any) -> str:
    return _normalize_label(str(value)).replace(" ", "")


def _normalize_label(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 2

    update = build_issue_title_update(event)
    if update is None:
        return 1

    print(json.dumps(update, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
