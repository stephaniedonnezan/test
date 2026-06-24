"""Build Linear title updates for issues moved to research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow state"}
TRIGGER_KEYS = ("trigger", "webhookType", "action", "type", "event", "eventType")
EXPLICIT_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "newWorkflowState",
    "new_workflow_state",
    "statusName",
    "status_name",
    "stateName",
    "state_name",
    "workflowStateName",
    "workflow_state_name",
)
FALLBACK_STATUS_KEYS = ("status", "state", "workflowState", "workflow_state")
ISSUE_ID_KEYS = ("issueId", "issue_id", "identifier", "key", "id")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to research.

    The Cursor automation payload is currently flat under ``triggerContext``,
    but tests cover nested Linear-style webhook payloads as well so the handler
    remains usable if the trigger source changes shape.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _context_candidates(event)
    if not _is_status_change_event(contexts):
        return None

    new_status = _extract_new_status(contexts)
    if _normalize(new_status) != TARGET_STATUS:
        return None

    issue_id = _extract_text(contexts, ISSUE_ID_KEYS)
    title = _extract_text(contexts, ("title",))
    if issue_id is None or title is None:
        return None

    trimmed_title = title.strip()
    if not trimmed_title or _has_prefix(trimmed_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {trimmed_title}",
    }


def _context_candidates(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []
    for candidate in (
        event.get("triggerContext"),
        event,
        event.get("data"),
        _mapping_get(event.get("data"), "issue"),
        event.get("issue"),
    ):
        if isinstance(candidate, Mapping) and candidate not in contexts:
            contexts.append(candidate)
    return contexts


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    generic_update_seen = False
    status_field_changed = False

    for context in contexts:
        for key in TRIGGER_KEYS:
            trigger_value = context.get(key)
            normalized = _normalize(trigger_value)
            if normalized in {"status changed", "status change"}:
                return True
            if normalized in {"update", "updated", "issue updated", "updated issue"}:
                generic_update_seen = True

        if _mentions_status_field(context.get("updatedFields")):
            status_field_changed = True
        if _mentions_status_field(context.get("changedFields")):
            status_field_changed = True
        if _changes_include_status(context.get("changes")):
            status_field_changed = True

    return generic_update_seen and status_field_changed


def _extract_new_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    for context in contexts:
        changed_status = _status_from_changes(context.get("changes"))
        if changed_status is not None:
            return changed_status

        updated_status = _status_from_updated_fields(context.get("updatedFields"))
        if updated_status is not None:
            return updated_status

    explicit_status = _extract_text(contexts, EXPLICIT_STATUS_KEYS)
    if explicit_status is not None:
        return explicit_status

    for context in contexts:
        for key in FALLBACK_STATUS_KEYS:
            value = context.get(key)
            text = _text_or_named_value(value)
            if text is not None:
                return text

    return None


def _extract_text(
    contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]
) -> str | None:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _status_from_changes(value: Any) -> str | None:
    if not isinstance(value, Mapping):
        return None

    for key, change in value.items():
        if _is_status_field(key):
            text = _new_value_from_change(change)
            if text is not None:
                return text

    return None


def _status_from_updated_fields(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key, change in value.items():
            if _is_status_field(key):
                return _new_value_from_change(change) or _text_or_named_value(change)

    if isinstance(value, list):
        for item in value:
            if isinstance(item, Mapping):
                field_name = item.get("field") or item.get("name") or item.get("key")
                if _is_status_field(field_name):
                    return _new_value_from_change(item)

    return None


def _new_value_from_change(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value

    if not isinstance(value, Mapping):
        return None

    for key in (
        "to",
        "after",
        "new",
        "newValue",
        "new_value",
        "newName",
        "new_name",
    ):
        text = _text_or_named_value(value.get(key))
        if text is not None:
            return text

    return None


def _text_or_named_value(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value
    if isinstance(value, Mapping):
        for key in ("name", "title"):
            nested = value.get(key)
            if isinstance(nested, str) and nested.strip():
                return nested
    return None


def _mentions_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field(value)
    if isinstance(value, Mapping):
        return any(_is_status_field(key) for key in value)
    if isinstance(value, list):
        for item in value:
            if isinstance(item, str) and _is_status_field(item):
                return True
            if isinstance(item, Mapping):
                field_name = item.get("field") or item.get("name") or item.get("key")
                if _is_status_field(field_name):
                    return True
    return False


def _changes_include_status(value: Any) -> bool:
    return isinstance(value, Mapping) and any(_is_status_field(key) for key in value)


def _mapping_get(value: Any, key: str) -> Any:
    if isinstance(value, Mapping):
        return value.get(key)
    return None


def _is_status_field(value: Any) -> bool:
    return _normalize(value) in STATUS_FIELDS


def _has_prefix(title: str) -> bool:
    return re.match(rf"^\s*{re.escape(PREFIX)}\b", title, re.IGNORECASE) is not None


def _normalize(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    words = re.sub(r"[^A-Za-z0-9]+", " ", spaced).strip().lower()
    return re.sub(r"\s+", " ", words)


def main() -> int:
    event = json.load(sys.stdin)
    result = build_issue_title_update(event)
    json.dump(result, sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
