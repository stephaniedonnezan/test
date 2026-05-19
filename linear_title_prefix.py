"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_CHANGE_EVENTS = {
    "status change",
    "status changed",
    "state change",
    "state changed",
    "workflow state change",
    "workflow state changed",
}
_ISSUE_UPDATE_EVENTS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}
_STATUS_FIELD_NAMES = {"status", "state", "workflowstate", "workflow_state", "workflow state"}
_NEW_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "newWorkflowState",
    "new_workflow_state",
)
_FALLBACK_STATUS_KEYS = ("status", "state", "workflowState", "workflow_state")
_ISSUE_ID_KEYS = ("id", "issueId", "issue_id", "identifier")


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to To Research."""
    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    status = _extract_status(event)
    if _normalize_text(status) != TARGET_STATUS:
        return None

    title = _extract_title(event)
    issue_id = _extract_issue_id(event)
    if not title or not issue_id:
        return None

    trimmed_title = title.strip()
    if _has_research_prefix(trimmed_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {trimmed_title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    for context in _iter_mappings(event):
        for key in ("trigger", "event", "eventType", "webhookType", "action", "type"):
            normalized = _normalize_text(context.get(key))
            if normalized in _STATUS_CHANGE_EVENTS:
                return True

    if not _has_issue_update_event(event):
        return False

    return _has_updated_status_field(event)


def _has_issue_update_event(event: Mapping[str, Any]) -> bool:
    for context in _iter_mappings(event):
        for key in ("trigger", "event", "eventType", "webhookType", "action", "type"):
            if _normalize_text(context.get(key)) in _ISSUE_UPDATE_EVENTS:
                return True
    return False


def _has_updated_status_field(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized_key = _normalize_text(key)
            if normalized_key in {"updated fields", "changed fields", "updated field names"}:
                if _contains_status_field(child):
                    return True
            if normalized_key in {"changes", "updated from", "previous values"}:
                if isinstance(child, Mapping) and any(_is_status_field_name(field) for field in child):
                    return True
                if _contains_status_field(child):
                    return True
            if _has_updated_status_field(child):
                return True
    elif isinstance(value, list | tuple):
        return any(_has_updated_status_field(item) for item in value)
    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field_name(value)
    if isinstance(value, Mapping):
        field_name = value.get("field") or value.get("name") or value.get("key")
        if field_name is not None and _is_status_field_name(field_name):
            return True
        return any(_is_status_field_name(key) or _contains_status_field(child) for key, child in value.items())
    if isinstance(value, Iterable):
        return any(_contains_status_field(item) for item in value)
    return False


def _is_status_field_name(value: Any) -> bool:
    normalized = _normalize_text(value)
    return normalized in _STATUS_FIELD_NAMES


def _extract_status(event: Mapping[str, Any]) -> str | None:
    for context in _iter_mappings(event):
        status = _first_value(context, _NEW_STATUS_KEYS)
        if status:
            return status

    for context in _iter_mappings(event):
        status = _first_value(context, _FALLBACK_STATUS_KEYS)
        if status:
            return status

    return None


def _extract_title(event: Mapping[str, Any]) -> str | None:
    for context in _iter_mappings(event):
        title = _scalar_text(context.get("title"))
        if title:
            return title
    return None


def _extract_issue_id(event: Mapping[str, Any]) -> str | None:
    for context in _iter_mappings(event):
        issue_id = _first_value(context, _ISSUE_ID_KEYS)
        if issue_id:
            return issue_id
    return None


def _first_value(context: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for key in keys:
        value = context.get(key)
        text = _status_text(value)
        if text:
            return text
    return None


def _status_text(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            text = _scalar_text(value.get(key))
            if text:
                return text
        return None
    return _scalar_text(value)


def _scalar_text(value: Any) -> str | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (str, int, float)):
        text = str(value).strip()
        return text or None
    return None


def _iter_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for child in value.values():
            yield from _iter_mappings(child)
    elif isinstance(value, list | tuple):
        for child in value:
            yield from _iter_mappings(child)


def _normalize_text(value: Any) -> str:
    text = _scalar_text(value)
    if not text:
        return ""

    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def main() -> int:
    payload = json.load(sys.stdin)
    result = build_issue_title_update(payload)
    if result is not None:
        print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
