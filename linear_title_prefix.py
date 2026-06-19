"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
PREFIXED_TITLE = f"{PREFIX}: {{title}}"
RESEARCH_STATUS = "to research"
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow status"}
ISSUE_UPDATE_EVENTS = {"update", "updated", "issue update", "issue updated", "updated issue"}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title-update action for status changes to To Research.

    The Cursor automation trigger payload is usually flat under
    ``automation_trigger_info.triggerContext``. Linear webhooks can also include
    nested ``data`` and ``issue`` objects. This function accepts both shapes and
    returns a small action object for the caller to apply.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)
    if not contexts:
        return None

    if not _is_status_change_event(contexts):
        return None

    if _normalize_status(_first_status(contexts)) != RESEARCH_STATUS:
        return None

    issue_id = _clean(_first_value(contexts, ("issueId", "issue_id", "identifier", "key", "id")))
    title = _clean(_first_value(contexts, ("title", "name")))
    if not issue_id or not title or _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": PREFIXED_TITLE.format(title=title),
    }


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Collect useful payload objects from outermost to innermost."""

    contexts: list[Mapping[str, Any]] = []

    def visit(value: Any) -> None:
        if not isinstance(value, Mapping):
            return
        contexts.append(value)
        for key in ("automation_trigger_info", "triggerContext", "data", "issue"):
            child = value.get(key)
            if isinstance(child, Mapping):
                visit(child)

    visit(event)
    return contexts


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    trigger_values: list[str] = []
    has_generic_update_event = False
    has_status_field_change = False

    for context in contexts:
        for key in ("trigger", "webhookType", "action", "type"):
            normalized = _normalize_event_name(context.get(key))
            if not normalized:
                continue
            trigger_values.append(normalized)
            if normalized in ISSUE_UPDATE_EVENTS:
                has_generic_update_event = True

        if _changed_status_fields(context):
            has_status_field_change = True

    if any("status changed" in value or "state changed" in value for value in trigger_values):
        return True

    return has_generic_update_event and has_status_field_change


def _changed_status_fields(context: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields"):
        if _contains_status_field(context.get(key)):
            return True

    changes = context.get("changes")
    if isinstance(changes, Mapping):
        if _contains_status_field(changes.keys()):
            return True
    elif isinstance(changes, list):
        for change in changes:
            if isinstance(change, Mapping) and _contains_status_field(change.keys()):
                return True
            if _contains_status_field(change):
                return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        candidates = [value]
    elif isinstance(value, Mapping):
        candidates = value.keys()
    elif isinstance(value, Iterable):
        candidates = value
    else:
        return False

    for candidate in candidates:
        normalized = _normalize_field_name(candidate)
        if normalized in STATUS_FIELDS:
            return True

    return False


def _first_status(contexts: Iterable[Mapping[str, Any]]) -> Any:
    explicit = _first_value(
        contexts,
        (
            "newStatus",
            "new_status",
            "newState",
            "new_state",
            "newWorkflowState",
            "new_workflow_state",
        ),
    )
    if explicit is not None:
        return explicit

    changed = _status_from_changes(contexts)
    if changed is not None:
        return changed

    for context in contexts:
        for key in ("status", "state", "workflowState", "workflow_state"):
            value = context.get(key)
            if isinstance(value, Mapping):
                nested = _first_value((value,), ("name", "title", "id"))
                if nested is not None:
                    return nested
            elif value is not None:
                return value

    return None


def _status_from_changes(contexts: Iterable[Mapping[str, Any]]) -> Any:
    for context in contexts:
        changes = context.get("changes")
        if not isinstance(changes, Mapping):
            continue

        for key, change in changes.items():
            if _normalize_field_name(key) not in STATUS_FIELDS:
                continue
            if isinstance(change, Mapping):
                value = _first_value((change,), ("newValue", "new_value", "to", "after", "name"))
                if isinstance(value, Mapping):
                    nested = _first_value((value,), ("name", "title", "id"))
                    if nested is not None:
                        return nested
                if value is not None:
                    return value
            return change

    return None


def _first_value(contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> Any:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if value is not None:
                return value
    return None


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def _normalize_status(value: Any) -> str | None:
    text = _clean(value)
    if not text:
        return None
    return _normalize_words(text)


def _normalize_event_name(value: Any) -> str | None:
    text = _clean(value)
    if not text:
        return None
    return _normalize_words(text)


def _normalize_field_name(value: Any) -> str:
    text = _clean(value) or ""
    return _normalize_words(text).replace(" ", "")


def _normalize_words(text: str) -> str:
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    return re.sub(r"[^a-z0-9]+", " ", spaced.lower()).strip()


def main() -> int:
    """Read a JSON event from stdin and print the title update action."""

    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
