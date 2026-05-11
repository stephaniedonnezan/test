"""Helpers for prefixing Linear issue titles during research automation."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"

_STATUS_CHANGE_TRIGGERS = {
    "status changed",
    "status change",
    "status updated",
    "state changed",
    "state change",
    "state updated",
}
_ISSUE_UPDATED_TRIGGERS = {"issue updated", "updated issue"}
_STATUS_FIELD_NAMES = {"status", "state", "workflow state"}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Build a Linear issue title update for status changes to research."""
    if not isinstance(event, Mapping):
        return None

    payload = _issue_payload(event)
    if not _is_status_change(event, payload):
        return None

    status = _first_text(
        (payload, event),
        "newStatus",
        "new_status",
        "status",
        "statusName",
        "stateName",
    ) or _nested_name(payload, "state") or _nested_name(payload, "workflowState")
    if _normalize(status) != _normalize(RESEARCH_STATUS):
        return None

    issue_id = _first_text((payload, event), "id", "issueId", "issue_id", "identifier")
    title = _first_text((payload, event), "title")
    if issue_id is None or title is None:
        return None

    title = title.strip()
    if not title or _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def handle_issue_status_changed(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Compatibility alias for handler-style automation runtimes."""
    return build_issue_title_update(event)


def _issue_payload(event: Mapping[str, Any]) -> Mapping[str, Any]:
    """Combine common Linear automation envelopes into one lookup surface."""
    payload: dict[str, Any] = dict(event)
    for key in ("triggerContext", "data", "issue"):
        value = event.get(key)
        if isinstance(value, Mapping):
            payload.update(value)
            nested_issue = value.get("issue")
            if isinstance(nested_issue, Mapping):
                payload.update(nested_issue)

    return payload


def _is_status_change(event: Mapping[str, Any], payload: Mapping[str, Any]) -> bool:
    trigger_values = [
        _as_text(source.get(key))
        for source in (event, payload)
        for key in ("trigger", "webhookType", "action", "type")
    ]
    normalized_triggers = {_normalize(value) for value in trigger_values if value}

    if any(value in _STATUS_CHANGE_TRIGGERS for value in normalized_triggers):
        return True

    if any(value in _ISSUE_UPDATED_TRIGGERS for value in normalized_triggers):
        updated_fields = payload.get("updatedFields") or payload.get("updated_fields")
        if isinstance(updated_fields, str):
            field_names = [updated_fields]
        elif isinstance(updated_fields, Mapping):
            field_names = list(updated_fields.keys())
        elif isinstance(updated_fields, (list, tuple, set, frozenset)):
            field_names = list(updated_fields)
        else:
            field_names = []
        return any(_normalize(_as_text(field)) in _STATUS_FIELD_NAMES for field in field_names)

    return False


def _first_text(sources: tuple[Mapping[str, Any], ...], *keys: str) -> str | None:
    for key in keys:
        for source in sources:
            value = _as_text(source.get(key))
            if value is not None:
                return value
    return None


def _nested_name(source: Mapping[str, Any], key: str) -> str | None:
    value = source.get(key)
    if isinstance(value, Mapping):
        return _as_text(value.get("name"))
    return None


def _as_text(value: Any) -> str | None:
    if isinstance(value, str):
        text = value.strip()
        return text or None
    return None


def _normalize(value: str | None) -> str | None:
    if value is None:
        return None

    words = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    words = re.sub(r"[^a-zA-Z0-9]+", " ", words)
    return " ".join(words.casefold().split())


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(TITLE_PREFIX.casefold())
