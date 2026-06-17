"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


RESEARCH_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_PREFIX_RE = re.compile(r"^\s*cursor\s+researching\b(?:\s*[:\-]\s*)?", re.IGNORECASE)
_CAMEL_BOUNDARY_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_STATUS_FIELD_NAMES = {"status", "state", "workflow state", "workflowstate"}
_DIRECT_STATUS_CHANGE_MARKERS = {
    "status changed",
    "status change",
    "state changed",
    "workflow state changed",
}
_GENERIC_UPDATE_MARKERS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action for a matching status-change event."""
    updated_title = derive_updated_title(event)
    if updated_title is None:
        return None

    issue_id = _extract_issue_id(event)
    if issue_id is None:
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": updated_title,
    }


def derive_updated_title(event: Mapping[str, Any]) -> str | None:
    """Derive the prefixed issue title, or ``None`` when no update is needed."""
    if not isinstance(event, Mapping):
        return None

    if not _is_issue_status_change(event):
        return None

    new_status = _extract_new_status(event)
    if _normalize_text(new_status) != TARGET_STATUS:
        return None

    title = _extract_title(event)
    if title is None:
        return None

    return prefix_research_title(title)


def prefix_research_title(title: str) -> str | None:
    """Prefix a title with the Cursor research marker unless it is already present."""
    stripped = title.strip()
    if not stripped or _PREFIX_RE.match(stripped):
        return None

    return f"{RESEARCH_PREFIX}: {stripped}"


def _extract_title(event: Mapping[str, Any]) -> str | None:
    return _first_text_value(event, ("title",))


def _extract_issue_id(event: Mapping[str, Any]) -> str | None:
    return _first_text_value(event, ("issueId", "issue_id", "identifier", "key", "id"))


def _extract_new_status(event: Mapping[str, Any]) -> str | None:
    status = _first_text_value(
        event,
        (
            "newStatus",
            "new_status",
            "newState",
            "new_state",
            "toStatus",
            "to_status",
            "statusName",
            "stateName",
            "workflowStateName",
        ),
    )
    if status is not None:
        return status

    for context in _walk_mappings(event):
        for key in ("status", "state", "workflowState", "workflow_state"):
            value = context.get(key)
            text = _text_from_status_value(value)
            if text is not None:
                return text

    return None


def _is_issue_status_change(event: Mapping[str, Any]) -> bool:
    if _has_non_issue_webhook_type(event):
        return False

    trigger_values = [
        _normalize_text(value)
        for context in _walk_mappings(event)
        for key, value in context.items()
        if key in {"trigger", "action", "type", "eventType", "event_type"}
    ]

    if any(marker in _DIRECT_STATUS_CHANGE_MARKERS for marker in trigger_values):
        return True

    has_generic_update = any(marker in _GENERIC_UPDATE_MARKERS for marker in trigger_values)
    if has_generic_update and _has_status_updated_field(event):
        return True

    return _first_text_value(event, ("newStatus", "new_status")) is not None and _has_status_updated_field(event)


def _has_non_issue_webhook_type(event: Mapping[str, Any]) -> bool:
    webhook_types = [
        _normalize_text(value)
        for context in _walk_mappings(event)
        for key, value in context.items()
        if key == "webhookType"
    ]
    return bool(webhook_types) and all(webhook_type != "issue" for webhook_type in webhook_types)


def _has_status_updated_field(event: Mapping[str, Any]) -> bool:
    for context in _walk_mappings(event):
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            if key in context and _contains_status_field(context[key]):
                return True

        changes = context.get("changes")
        if isinstance(changes, Mapping) and any(_is_status_field_name(key) for key in changes):
            return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field_name(value)

    if isinstance(value, Mapping):
        return any(
            _contains_status_field(value.get(key))
            for key in ("field", "fieldName", "name", "key", "property")
            if key in value
        )

    if isinstance(value, Iterable):
        return any(_contains_status_field(item) for item in value)

    return False


def _is_status_field_name(value: Any) -> bool:
    normalized = _normalize_text(value)
    return normalized in _STATUS_FIELD_NAMES


def _first_text_value(event: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for context in _preferred_contexts(event):
        for key in keys:
            if key not in context:
                continue
            value = _text_from_status_value(context[key])
            if value is not None:
                return value

    return None


def _text_from_status_value(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None

    if isinstance(value, Mapping):
        return _first_text_value(value, ("name", "title", "label", "id", "identifier", "key"))

    return None


def _preferred_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
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

    seen: set[int] = set()
    unique_contexts: list[Mapping[str, Any]] = []
    for context in contexts:
        context_id = id(context)
        if context_id not in seen:
            seen.add(context_id)
            unique_contexts.append(context)

    return unique_contexts


def _walk_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if not isinstance(value, Mapping):
        return

    yield value
    for nested_value in value.values():
        if isinstance(nested_value, Mapping):
            yield from _walk_mappings(nested_value)
        elif isinstance(nested_value, list):
            for item in nested_value:
                yield from _walk_mappings(item)


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""

    text = _CAMEL_BOUNDARY_RE.sub(" ", str(value).strip())
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def main() -> int:
    """Read a JSON event from stdin and print the update action as JSON."""
    event = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(event), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
