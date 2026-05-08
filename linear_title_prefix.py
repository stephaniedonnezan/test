"""Helpers for Linear issue title updates from Cursor automation events."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Build a Linear title update when an issue enters the research status.

    The automation payloads can be flat or nested under keys such as
    ``triggerContext``, ``data.issue``, and ``issue``.  This function keeps the
    decision small and deterministic: only status-change events moving to
    "to research" receive the Cursor research prefix.
    """

    if not isinstance(event, Mapping):
        return None

    combined = _combined_issue_data(event)
    if not _is_status_change_event(event):
        return None

    status = _lookup_text(combined, ("newStatus", "new_status", "status", "state"))
    if _normalize_words(status) != TARGET_STATUS:
        return None

    issue_id = _lookup_text(combined, ("id", "issueId", "issue_id", "identifier"))
    title = _lookup_text(combined, ("title",))
    if not issue_id or not title:
        return None

    issue_id = issue_id.strip()
    title = title.strip()
    if not issue_id or not title or _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _combined_issue_data(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge likely issue payload locations, letting outer metadata win."""

    combined: dict[str, Any] = {}
    for path in (
        ("data", "issue"),
        ("issue",),
        ("data",),
        ("triggerContext", "data", "issue"),
        ("triggerContext", "issue"),
        ("triggerContext",),
        (),
    ):
        value = _dig(event, path)
        if isinstance(value, Mapping):
            combined.update(value)

    return combined


def _dig(source: Mapping[str, Any], path: tuple[str, ...]) -> Any:
    value: Any = source
    for key in path:
        if not isinstance(value, Mapping):
            return None
        value = value.get(key)
    return value


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    for payload in _iter_mappings(event):
        for key in ("trigger", "action", "type", "eventType", "event_type"):
            trigger = _normalize_words(payload.get(key))
            if _is_direct_status_change_trigger(trigger):
                return True
            if _is_issue_updated_trigger(trigger) and _updated_fields_include_status(event):
                return True

    return False


def _iter_mappings(value: Any, depth: int = 0) -> Iterable[Mapping[str, Any]]:
    if depth > 4 or not isinstance(value, Mapping):
        return

    yield value
    for nested in value.values():
        if isinstance(nested, Mapping):
            yield from _iter_mappings(nested, depth + 1)


def _is_direct_status_change_trigger(trigger: str) -> bool:
    return trigger in {
        "status changed",
        "status change",
        "status updated",
        "state changed",
        "state change",
        "state updated",
    }


def _is_issue_updated_trigger(trigger: str) -> bool:
    return trigger in {
        "issue updated",
        "issue update",
        "updated issue",
        "update issue",
    }


def _updated_fields_include_status(event: Mapping[str, Any]) -> bool:
    for payload in _iter_mappings(event):
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            fields = payload.get(key)
            if _field_collection_includes_status(fields):
                return True
        changes = payload.get("changes")
        if isinstance(changes, Mapping) and _field_collection_includes_status(changes.keys()):
            return True

    return False


def _field_collection_includes_status(fields: Any) -> bool:
    if isinstance(fields, Mapping):
        field_names = fields.keys()
    elif isinstance(fields, Iterable) and not isinstance(fields, (str, bytes)):
        field_names = fields
    else:
        return False

    return any(_normalize_words(field) in {"status", "state"} for field in field_names)


def _lookup_text(source: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        if key not in source:
            continue

        value = source[key]
        if key == "state" and isinstance(value, Mapping):
            value = value.get("name")

        if isinstance(value, str):
            return value

    return None


def _normalize_words(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    value = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    words = re.sub(r"[^A-Za-z0-9]+", " ", value).strip().lower().split()
    return " ".join(words)


def _has_research_prefix(title: str) -> bool:
    return re.match(rf"^\s*{re.escape(TITLE_PREFIX)}\b", title, re.IGNORECASE) is not None
