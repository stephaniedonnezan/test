"""Build Linear issue title updates for research status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_FIELD_NAMES = {"status", "state", "workflow state", "workflowstate"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when an issue moves to "to research"."""
    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    if _normalized_status(_new_status(event)) != TARGET_STATUS:
        return None

    issue_id = _first_text(event, ("id", "issueId", "issue_id", "identifier", "key"))
    title = _first_text(event, ("title", "name"))
    if not issue_id or not title or _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    event_types = [
        _normalized_words(value)
        for context in _context_mappings(event)
        for key in ("trigger", "webhookType", "action", "type")
        for value in [context.get(key)]
        if value is not None
    ]

    if any(event_type in {"status changed", "status change"} for event_type in event_types):
        return True

    if any(event_type in {"update", "updated", "issue updated", "updated issue"} for event_type in event_types):
        return _mentions_status_field(event)

    return False


def _new_status(event: Mapping[str, Any]) -> Any:
    explicit_keys = (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "newWorkflowState",
        "new_workflow_state",
        "toStatus",
        "to_status",
        "statusNew",
        "status_new",
    )
    for context in _context_mappings(event):
        for key in explicit_keys:
            if key in context:
                return context[key]

    changed_status = _status_from_changes(event)
    if changed_status is not None:
        return changed_status

    for context in _context_mappings(event):
        for key in ("status", "state", "workflowState", "workflow_state"):
            if key in context:
                return context[key]

    return None


def _status_from_changes(value: Any) -> Any:
    for mapping in _walk_mappings(value):
        changes = mapping.get("changes")
        if isinstance(changes, Mapping):
            for key, change in changes.items():
                if not _is_status_field_name(key):
                    continue

                if isinstance(change, Mapping):
                    for target_key in ("to", "new", "after", "toValue", "newValue", "value"):
                        if target_key in change:
                            return change[target_key]
                return change

        change = mapping.get("change")
        if isinstance(change, Mapping):
            field_name = change.get("field") or change.get("fieldName") or change.get("name")
            if _is_status_field_name(field_name):
                for target_key in ("to", "new", "after", "toValue", "newValue", "value"):
                    if target_key in change:
                        return change[target_key]

    return None


def _mentions_status_field(value: Any) -> bool:
    for mapping in _walk_mappings(value):
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            if key in mapping and any(_is_status_field_name(field) for field in _field_names(mapping[key])):
                return True

        changes = mapping.get("changes")
        if isinstance(changes, Mapping) and any(_is_status_field_name(key) for key in changes):
            return True

        change = mapping.get("change")
        if isinstance(change, Mapping):
            field_name = change.get("field") or change.get("fieldName") or change.get("name")
            if _is_status_field_name(field_name):
                return True

    return False


def _field_names(value: Any) -> Iterable[Any]:
    if isinstance(value, str):
        yield value
        return

    if isinstance(value, Mapping):
        yield from value.keys()
        for key in ("field", "fieldName", "name"):
            if key in value:
                yield value[key]
        return

    if isinstance(value, Iterable):
        for item in value:
            if isinstance(item, Mapping):
                for key in ("field", "fieldName", "name"):
                    if key in item:
                        yield item[key]
            else:
                yield item


def _first_text(event: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for context in _context_mappings(event):
        for key in keys:
            text = _text_value(context.get(key))
            if text:
                return text
    return None


def _context_mappings(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        contexts.append(trigger_context)

    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            contexts.append(issue)
        contexts.append(data)

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        contexts.append(issue)

    contexts.append(event)
    return contexts


def _walk_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for nested in value.values():
            yield from _walk_mappings(nested)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_mappings(item)


def _normalized_status(value: Any) -> str:
    return _normalized_words(_status_text(value))


def _normalized_words(value: Any) -> str:
    text = _text_value(value)
    if not text:
        return ""

    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def _status_text(value: Any) -> Any:
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            if key in value:
                return value[key]
    return value


def _text_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        value = _status_text(value)

    if value is None:
        return None

    text = str(value).strip()
    return text or None


def _is_status_field_name(value: Any) -> bool:
    normalized = _normalized_words(value)
    return normalized in STATUS_FIELD_NAMES


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        json.dump(update, sys.stdout)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
