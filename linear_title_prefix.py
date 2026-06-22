"""Build Linear issue title updates for research-status automation."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELDS = {"status", "state", "workflowstate", "workflow state"}
_DIRECT_STATUS_CHANGE_TRIGGERS = {"status changed", "statuschange", "status changed"}
_ISSUE_UPDATE_TRIGGERS = {"issue updated", "updated issue", "update", "updated"}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update action when an issue enters the to-research status."""

    if not isinstance(event, Mapping):
        return None

    contexts = _collect_contexts(event)
    if not _is_status_change_event(contexts):
        return None

    new_status = _extract_new_status(contexts)
    if _normalize_words(new_status) != TARGET_STATUS:
        return None

    issue_id = _extract_issue_id(contexts)
    title = _extract_first_string(contexts, ("title",))
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _collect_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Collect likely metadata and issue objects, with outer metadata first."""

    contexts: list[Mapping[str, Any]] = []
    seen: set[int] = set()

    def add(value: Any) -> None:
        if not isinstance(value, Mapping):
            return
        value_id = id(value)
        if value_id in seen:
            return
        seen.add(value_id)
        contexts.append(value)

    add(event)

    for key in ("automation_trigger_info", "triggerContext", "data", "issue"):
        value = event.get(key)
        add(value)

        if isinstance(value, Mapping):
            for nested_key in ("triggerContext", "data", "issue"):
                add(value.get(nested_key))

    return contexts


def _is_status_change_event(contexts: list[Mapping[str, Any]]) -> bool:
    if _has_direct_status_change_trigger(contexts):
        return True

    if _has_issue_update_trigger(contexts) and _has_status_updated_field(contexts):
        return True

    return _has_status_change_payload(contexts) and not _has_explicit_non_status_trigger(contexts)


def _has_direct_status_change_trigger(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("trigger", "webhookType", "webhook_type", "action", "type", "eventType"):
            value = context.get(key)
            normalized = _normalize_words(value)
            if normalized in _DIRECT_STATUS_CHANGE_TRIGGERS:
                return True
            if "status" in normalized and "changed" in normalized:
                return True
    return False


def _has_issue_update_trigger(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("trigger", "webhookType", "webhook_type", "action", "type", "eventType"):
            if _normalize_words(context.get(key)) in _ISSUE_UPDATE_TRIGGERS:
                return True
    return False


def _has_explicit_non_status_trigger(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("trigger", "action", "eventType"):
            normalized = _normalize_words(context.get(key))
            if not normalized:
                continue
            if normalized in _DIRECT_STATUS_CHANGE_TRIGGERS or normalized in _ISSUE_UPDATE_TRIGGERS:
                continue
            return True
    return False


def _has_status_updated_field(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        updated_fields = context.get("updatedFields") or context.get("updated_fields")
        if _contains_status_field(updated_fields):
            return True

        changes = context.get("changes")
        if isinstance(changes, Mapping) and any(_is_status_field(key) for key in changes):
            return True
        if _contains_status_field(changes):
            return True
    return False


def _has_status_change_payload(contexts: list[Mapping[str, Any]]) -> bool:
    for context in contexts:
        for key in ("newStatus", "new_status", "newState", "new_state", "newWorkflowState"):
            if _string_from_value(context.get(key)):
                return True

        changes = context.get("changes")
        if isinstance(changes, Mapping) and any(_extract_change_new_value(changes.get(key)) for key in changes if _is_status_field(key)):
            return True

    return False


def _extract_new_status(contexts: list[Mapping[str, Any]]) -> str | None:
    for key in ("newStatus", "new_status", "newState", "new_state", "newWorkflowState"):
        value = _extract_first_string(contexts, (key,))
        if value:
            return value

    for context in contexts:
        changes = context.get("changes")
        if not isinstance(changes, Mapping):
            continue
        for key, value in changes.items():
            if not _is_status_field(key):
                continue
            new_value = _extract_change_new_value(value)
            if new_value:
                return new_value

    for key in ("status", "state", "workflowState", "workflow_state"):
        value = _extract_first_string(contexts, (key,))
        if value:
            return value

    return None


def _extract_change_new_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("to", "new", "newValue", "new_value", "after", "name", "title"):
            text = _string_from_value(value.get(key))
            if text:
                return text
    return _string_from_value(value)


def _extract_issue_id(contexts: list[Mapping[str, Any]]) -> str | None:
    return _extract_first_string(contexts, ("issueId", "issue_id", "identifier", "key")) or _extract_first_string(contexts, ("id",))


def _extract_first_string(contexts: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for context in contexts:
        for key in keys:
            value = _string_from_value(context.get(key))
            if value:
                return value
    return None


def _string_from_value(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "identifier", "key", "id"):
            text = _string_from_value(value.get(key))
            if text:
                return text

    return None


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)

    if isinstance(value, Mapping):
        return any(_is_status_field(key) or _contains_status_field(nested) for key, nested in value.items())

    if isinstance(value, list | tuple | set):
        return any(_contains_status_field(item) for item in value)

    return False


def _is_status_field(value: Any) -> bool:
    return _normalize_words(value) in _STATUS_FIELDS


def _has_research_prefix(title: str) -> bool:
    return title.lstrip().lower().startswith(PREFIX.lower())


def _normalize_words(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    separated = re.sub(r"[^A-Za-z0-9]+", " ", spaced)
    return " ".join(separated.lower().split())


def main() -> int:
    update = build_issue_title_update(json.load(sys.stdin))
    print(json.dumps(update, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
