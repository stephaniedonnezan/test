"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow state"}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title-update action when an issue moves to "to research".

    The function accepts both the flat Cursor automation payload shape and
    nested Linear webhook shapes. It is intentionally side-effect free so the
    caller can decide how to apply the returned update.
    """

    if not _is_mapping(event):
        return None

    contexts = list(_candidate_contexts(event))
    if not _is_status_change_event(contexts):
        return None

    new_status = _extract_new_status(contexts)
    if _normalize_words(new_status) != TARGET_STATUS:
        return None

    title = _find_text(contexts, ("title", "name", "summary"))
    issue_id = _find_text(contexts, ("issueId", "issue_id", "identifier", "key", "id"))
    if not title or not issue_id:
        return None

    clean_title = title.strip()
    if not clean_title or _has_research_prefix(clean_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {clean_title}",
    }


def handle_issue_status_changed(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Compatibility wrapper for callers with status-change specific naming."""

    return build_issue_title_update(event)


def _candidate_contexts(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield likely payload locations from most-specific to most-general."""

    seen: set[int] = set()

    def add(value: Any) -> Iterable[Mapping[str, Any]]:
        if _is_mapping(value) and id(value) not in seen:
            seen.add(id(value))
            yield value

    automation_info = event.get("automation_trigger_info") or event.get("automationTriggerInfo")
    if _is_mapping(automation_info):
        yield from add(automation_info.get("triggerContext"))
        yield from add(automation_info.get("trigger_context"))

    yield from add(event.get("triggerContext"))
    yield from add(event.get("trigger_context"))
    yield from add(event)

    data = event.get("data")
    if _is_mapping(data):
        issue = data.get("issue") or data.get("node")
        yield from add(issue)
        yield from add(data)

    yield from add(event.get("issue"))
    yield from add(event.get("node"))


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    contexts = list(contexts)
    if any(_is_direct_status_change_value(context.get(key)) for context in contexts for key in ("trigger", "event", "type", "webhookType", "webhook_type")):
        return True

    has_update_action = any(
        _normalize_words(context.get(key)) in {"update", "updated", "issue update", "issue updated", "updated issue"}
        for context in contexts
        for key in ("action", "event", "type", "webhookType", "webhook_type", "trigger")
    )
    return has_update_action and any(_has_status_update_marker(context) for context in contexts)


def _is_direct_status_change_value(value: Any) -> bool:
    normalized = _normalize_words(value)
    return normalized in {"status changed", "status change", "status updated", "state changed", "workflow state changed"}


def _has_status_update_marker(context: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        if _field_list_contains_status(context.get(key)):
            return True

    for key in ("changes", "changed", "updatedFrom", "updated_from"):
        changes = context.get(key)
        if _is_mapping(changes) and any(_is_status_field_name(field) for field in changes):
            return True

    return False


def _field_list_contains_status(fields: Any) -> bool:
    if isinstance(fields, str):
        return _is_status_field_name(fields)

    if not isinstance(fields, Iterable):
        return False

    for field in fields:
        if _is_status_field_name(field):
            return True
        if _is_mapping(field):
            values = (field.get("name"), field.get("field"), field.get("key"), field.get("fieldName"))
            if any(_is_status_field_name(value) for value in values):
                return True
    return False


def _is_status_field_name(value: Any) -> bool:
    normalized = _normalize_words(value)
    return normalized in STATUS_FIELD_NAMES


def _extract_new_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    contexts = list(contexts)
    explicit_keys = (
        "newStatus",
        "new_status",
        "newStatusName",
        "new_status_name",
        "toStatus",
        "to_status",
        "toState",
        "to_state",
        "statusName",
        "status_name",
    )
    status = _find_text(contexts, explicit_keys)
    if status:
        return status

    for context in contexts:
        status = _status_from_changes(context.get("changes") or context.get("changed"))
        if status:
            return status

    return _find_text(contexts, ("status", "state", "workflowState", "workflow_state"))


def _status_from_changes(changes: Any) -> str | None:
    if not _is_mapping(changes):
        return None

    for field, change in changes.items():
        if not _is_status_field_name(field):
            continue

        if _is_mapping(change):
            for key in ("to", "new", "after", "current", "value", "name"):
                value = _text_from_value(change.get(key))
                if value:
                    return value
        else:
            value = _text_from_value(change)
            if value:
                return value

    return None


def _find_text(contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for context in contexts:
        for key in keys:
            value = _text_from_value(context.get(key))
            if value:
                return value
    return None


def _text_from_value(value: Any) -> str | None:
    if value is None:
        return None
    if _is_mapping(value):
        for key in ("name", "title", "identifier", "key", "id"):
            text = _text_from_value(value.get(key))
            if text:
                return text
        return None
    if isinstance(value, (str, int, float)):
        text = str(value).strip()
        return text or None
    return None


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())


def _normalize_words(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().casefold()


def _is_mapping(value: Any) -> bool:
    return isinstance(value, Mapping)


def main() -> int:
    """Read a JSON event from stdin and print the computed action."""

    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON payload: {exc}", file=sys.stderr)
        return 1

    action = build_issue_title_update(event)
    json.dump(action, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
