"""Build Linear issue title updates for issues entering research."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"

_STATUS_FIELD_NAMES = {"status", "state", "workflow state", "workflow status"}
_TRIGGER_KEYS = (
    "trigger",
    "webhookType",
    "webhook_type",
    "action",
    "type",
    "event",
    "eventType",
    "event_type",
)
_DIRECT_STATUS_CHANGE_TRIGGERS = {
    "status changed",
    "status change",
    "status updated",
    "state changed",
    "state change",
    "workflow state changed",
}
_ISSUE_UPDATE_TRIGGERS = {
    "issue updated",
    "issue update",
    "updated issue",
    "updated",
    "update",
}
_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "toStatus",
    "to_status",
    "statusName",
    "status_name",
    "stateName",
    "state_name",
    "workflowStateName",
    "workflow_state_name",
    "status",
)
_ISSUE_ID_KEYS = ("id", "issueId", "issue_id", "identifier", "key")
_TITLE_KEYS = ("title", "name", "summary")
_TITLE_PREFIX_PATTERN = re.compile(r"^\s*cursor researching(?:\b|[:|\-])", re.IGNORECASE)


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to research.

    Cursor automation payloads put issue metadata under ``triggerContext`` while
    Linear webhooks often nest the issue under ``data.issue``. This function
    accepts those common shapes and returns ``None`` unless the event represents
    a status change to "to research" and the title still needs the prefix.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _collect_contexts(event)
    if not _is_status_change_event(contexts):
        return None

    if _normalize_label(_extract_status(contexts)) != TARGET_STATUS:
        return None

    issue_id = _first_text(contexts, _ISSUE_ID_KEYS)
    title = _first_text(contexts, _TITLE_KEYS)
    if not issue_id or not title:
        return None

    next_title = with_title_prefix(title)
    if next_title == title.strip():
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id.strip(),
        "title": next_title,
    }


def handle_issue_status_changed(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Automation entrypoint alias."""

    return build_issue_title_update(event)


def with_title_prefix(title: str) -> str:
    """Return ``title`` with a single Cursor researching prefix."""

    stripped_title = title.strip()
    if not stripped_title:
        return TITLE_PREFIX

    if _has_title_prefix(stripped_title):
        return stripped_title

    return f"{TITLE_PREFIX}: {stripped_title}"


def _collect_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []

    def add_context(value: Any) -> None:
        if isinstance(value, Mapping) and not any(value is context for context in contexts):
            contexts.append(value)

    add_context(event.get("triggerContext"))

    for container_key in ("data", "payload", "webhook"):
        container = event.get(container_key)
        if isinstance(container, Mapping):
            add_context(container.get("issue"))

    add_context(event.get("issue"))

    for container_key in ("data", "payload", "webhook"):
        add_context(event.get(container_key))

    add_context(event)
    return contexts


def _is_status_change_event(contexts: Iterable[Mapping[str, Any]]) -> bool:
    trigger_values = [
        value
        for context in contexts
        for key in _TRIGGER_KEYS
        if isinstance((value := context.get(key)), str)
    ]
    normalized_triggers = {_normalize_label(value) for value in trigger_values}

    if normalized_triggers.intersection(_DIRECT_STATUS_CHANGE_TRIGGERS):
        return True

    changed_fields = _extract_changed_fields(contexts)
    if changed_fields:
        return any(_is_status_field(field) for field in changed_fields)

    return bool(normalized_triggers.intersection(_ISSUE_UPDATE_TRIGGERS)) and any(
        _context_has_status(context) for context in contexts
    )


def _extract_changed_fields(contexts: Iterable[Mapping[str, Any]]) -> list[str]:
    changed_fields: list[str] = []
    for context in contexts:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            value = context.get(key)
            if isinstance(value, str):
                changed_fields.append(value)
            elif isinstance(value, Mapping):
                changed_fields.extend(str(field) for field in value)
            elif isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
                changed_fields.extend(str(field) for field in value)
    return changed_fields


def _extract_status(contexts: Iterable[Mapping[str, Any]]) -> str | None:
    for key in _STATUS_KEYS:
        for context in contexts:
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value

    for context in contexts:
        for key in ("state", "workflowState", "workflow_state"):
            value = context.get(key)
            if isinstance(value, Mapping):
                name = value.get("name") or value.get("title")
                if isinstance(name, str) and name.strip():
                    return name

    return None


def _first_text(contexts: Iterable[Mapping[str, Any]], keys: Iterable[str]) -> str | None:
    for context in contexts:
        for key in keys:
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return None


def _context_has_status(context: Mapping[str, Any]) -> bool:
    return any(key in context for key in (*_STATUS_KEYS, "state", "workflowState", "workflow_state"))


def _is_status_field(value: str) -> bool:
    return _normalize_label(value) in _STATUS_FIELD_NAMES


def _has_title_prefix(title: str) -> bool:
    return bool(_TITLE_PREFIX_PATTERN.match(title))


def _normalize_label(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    words = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value.strip())
    words = re.sub(r"[^A-Za-z0-9]+", " ", words)
    return " ".join(words.casefold().split())


def main() -> int:
    """Read an event JSON object from stdin and print an update action if needed."""

    update = build_issue_title_update(json.load(sys.stdin))
    if update is not None:
        print(json.dumps(update))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
