"""Helpers for prefixing Linear issue titles during research handoff.

The automation layer is expected to call ``build_issue_title_update`` with the
Linear webhook payload. When the payload represents an issue status change to
"to research", the function returns the title update request the caller should
send to Linear.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


RESEARCH_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_CAMEL_BOUNDARY_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_NON_WORD_RE = re.compile(r"[^a-z0-9]+")


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Build a Linear issue title update for status changes to research.

    Returns ``None`` when the payload is not an issue status-change event, when
    the new status is not "to research", or when the title is already prefixed.
    """

    if not isinstance(event, Mapping):
        return None

    payload = _flatten_event(event)
    if not _is_status_change_event(payload):
        return None

    status = _first_text(
        payload,
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "status",
        "state.name",
        "workflowState.name",
        "workflow_state.name",
    )
    if _normalize(status) != TARGET_STATUS:
        return None

    issue_id = _first_text(payload, "id", "issueId", "issue_id", "identifier")
    title = _first_text(payload, "title", "name")
    if not issue_id or not title:
        return None

    title = title.strip()
    if not title or _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{RESEARCH_PREFIX}: {title}",
    }


def _flatten_event(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common Linear webhook nesting into one lookup context."""

    data = _mapping(event.get("data"))
    trigger_context = _mapping(event.get("triggerContext"))
    issue = _mapping(event.get("issue"))
    data_issue = _mapping(data.get("issue")) if data else {}
    trigger_issue = (
        _mapping(trigger_context.get("issue")) if trigger_context else {}
    )

    payload: dict[str, Any] = {}
    for source in (data_issue, trigger_issue, issue, data, trigger_context, event):
        _merge_present_values(payload, source)

    return payload


def _merge_present_values(target: dict[str, Any], source: Mapping[str, Any]) -> None:
    for key, value in source.items():
        if value is not None:
            target[key] = value


def _is_status_change_event(payload: Mapping[str, Any]) -> bool:
    trigger = _first_text(payload, "trigger", "webhookType", "action", "type")
    normalized_trigger = _normalize(trigger)

    if normalized_trigger in {"status changed", "status change", "status updated"}:
        return True

    if normalized_trigger in {"issue updated", "updated issue"}:
        return _updated_fields_include_status(payload.get("updatedFields"))

    return False


def _updated_fields_include_status(updated_fields: Any) -> bool:
    status_fields = {"status", "state", "workflow state", "workflowstatus"}

    if isinstance(updated_fields, str):
        return _normalize(updated_fields) in status_fields

    if isinstance(updated_fields, Mapping):
        return any(_normalize(field) in status_fields for field in updated_fields)

    if isinstance(updated_fields, list | tuple | set):
        return any(_normalize(field) in status_fields for field in updated_fields)

    return False


def _first_text(payload: Mapping[str, Any], *paths: str) -> str | None:
    for path in paths:
        value = _value_at_path(payload, path)
        if value is not None:
            text = str(value).strip()
            if text:
                return text
    return None


def _value_at_path(payload: Mapping[str, Any], path: str) -> Any:
    current: Any = payload
    for part in path.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return None
        current = current[part]
    return current


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _normalize(value: Any) -> str:
    if value is None:
        return ""

    spaced = _CAMEL_BOUNDARY_RE.sub(" ", str(value))
    words = _NON_WORD_RE.sub(" ", spaced.lower()).strip().split()
    return " ".join(words)


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(RESEARCH_PREFIX.lower())
