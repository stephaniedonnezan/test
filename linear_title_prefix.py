"""Build Linear issue title updates for research-status automations."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_CHANGED_TRIGGER = "status changed"


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update when an issue moves to "to research".

    The automation payloads used in tests and production-like triggers can be
    either flat or nested under keys such as ``triggerContext``, ``data``, and
    ``issue``. This function tolerates those shapes while keeping the behavioral
    contract intentionally small: only status-change events moving to the target
    status receive the prefix, and already-prefixed titles are left untouched.
    """

    if not isinstance(event, Mapping):
        return None

    contexts = _contexts(event)

    if not _is_status_change(contexts):
        return None

    if _normalize(_first_text(contexts, ("newStatus", "new_status", "status"))) != TARGET_STATUS:
        state_name = _first_text(_nested_mappings(contexts, "state"), ("name",))
        if _normalize(state_name) != TARGET_STATUS:
            return None

    issue_id = _first_text(contexts, ("id", "issueId", "issue_id", "identifier"))
    title = _first_text(contexts, ("title", "name"))

    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def handle_issue_status_changed(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Compatibility wrapper for callers that use handler-style naming."""

    return build_issue_title_update(event)


def handleIssueStatusChanged(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Compatibility wrapper for camelCase handler naming."""

    return build_issue_title_update(event)


def _contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = [event]

    for key in ("triggerContext", "data", "issue"):
        value = event.get(key)
        if isinstance(value, Mapping):
            contexts.append(value)

    for parent_key in ("triggerContext", "data"):
        parent = event.get(parent_key)
        if not isinstance(parent, Mapping):
            continue
        for child_key in ("data", "issue"):
            value = parent.get(child_key)
            if isinstance(value, Mapping):
                contexts.append(value)

    return contexts


def _nested_mappings(contexts: list[Mapping[str, Any]], key: str) -> list[Mapping[str, Any]]:
    nested: list[Mapping[str, Any]] = []
    for context in contexts:
        value = context.get(key)
        if isinstance(value, Mapping):
            nested.append(value)
    return nested


def _is_status_change(contexts: list[Mapping[str, Any]]) -> bool:
    for value in _field_values(contexts, ("trigger", "action", "type", "eventType", "event_type")):
        if _normalize(value) == STATUS_CHANGED_TRIGGER:
            return True
    return False


def _first_text(contexts: list[Mapping[str, Any]], keys: tuple[str, ...]) -> str | None:
    for value in _field_values(contexts, keys):
        if isinstance(value, str):
            stripped = value.strip()
            if stripped:
                return stripped
    return None


def _field_values(contexts: list[Mapping[str, Any]], keys: tuple[str, ...]) -> list[Any]:
    values: list[Any] = []
    for context in contexts:
        for key in keys:
            if key in context:
                values.append(context[key])
    return values


def _normalize(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    return re.sub(r"[^a-z0-9]+", " ", spaced.lower()).strip()


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())
