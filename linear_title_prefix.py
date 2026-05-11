"""Build Linear issue title updates for research status transitions."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title-update action when an issue moves to research.

    The automation trigger payloads seen in Cursor/Linear integrations can be
    flat, nested under ``triggerContext``, or nested under Linear's ``data``
    object. This function keeps the public contract small while accepting those
    shapes.
    """

    if not isinstance(event, Mapping):
        return None

    context = _merged_context(event)
    if not _is_status_change_event(context):
        return None

    if _normalize_words(_status_from(context)) != TARGET_STATUS:
        return None

    issue_id = _string_from(context, "id", "issueId", "issue_id", "identifier")
    title = _string_from(context, "title")
    if not issue_id or not title:
        return None

    clean_title = title.strip()
    if not clean_title or clean_title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {clean_title}",
    }


def _merged_context(event: Mapping[str, Any]) -> dict[str, Any]:
    context: dict[str, Any] = {}
    for part in _context_layers(event):
        context.update(part)
    return context


def _context_layers(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    trigger_context = _mapping_from(event, "triggerContext")
    data = _mapping_from(event, "data")
    trigger_data = _mapping_from(trigger_context, "data")

    return [
        _mapping_from(data, "issue"),
        _mapping_from(trigger_data, "issue"),
        _mapping_from(trigger_context, "issue"),
        data,
        trigger_data,
        trigger_context,
        event,
    ]


def _is_status_change_event(context: Mapping[str, Any]) -> bool:
    trigger = _normalize_words(
        _string_from(context, "trigger", "webhookType", "action", "type")
    )
    if trigger in {"status changed", "status change", "status updated"}:
        return True

    if trigger in {"issue updated", "updated issue"}:
        updated_fields = context.get("updatedFields", context.get("updated_fields"))
        return _mentions_status(updated_fields)

    return False


def _mentions_status(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_words(value) in {"status", "state", "workflow state"}

    if isinstance(value, Mapping):
        return any(_mentions_status(key) or _mentions_status(item) for key, item in value.items())

    if isinstance(value, list | tuple | set | frozenset):
        return any(_mentions_status(item) for item in value)

    return False


def _status_from(context: Mapping[str, Any]) -> str | None:
    direct_status = _string_from(context, "newStatus", "new_status", "status")
    if direct_status:
        return direct_status

    for key in ("state", "workflowState", "workflow_state"):
        status = _string_from(_mapping_from(context, key), "name")
        if status:
            return status

    return None


def _string_from(mapping: Mapping[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, str):
            return value
    return None


def _mapping_from(mapping: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = mapping.get(key)
    return value if isinstance(value, Mapping) else {}


def _normalize_words(value: str | None) -> str:
    if value is None:
        return ""

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return re.sub(r"[^a-z0-9]+", " ", spaced.lower()).strip()
