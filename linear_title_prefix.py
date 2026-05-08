"""Build title update actions for Linear issue status-change events."""

from __future__ import annotations

import re
from collections.abc import Iterator, Mapping
from typing import Any


RESEARCH_STATUS = "to research"
TITLE_PREFIX = "Cursor researching"
UPDATE_ACTION = "update_issue_title"


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to research."""
    if not isinstance(event, Mapping):
        return None

    context = _event_context(event)

    if not _is_status_change(context):
        return None

    if _normalize_text(_new_status(context)) != RESEARCH_STATUS:
        return None

    issue_id = _first_text(context, ("id", "issueId", "issue_id", "identifier"))
    title = _first_text(context, ("title", "name"))
    if not issue_id or not title:
        return None

    stripped_title = title.strip()
    if _has_research_prefix(stripped_title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id.strip(),
        "title": f"{TITLE_PREFIX}: {stripped_title}",
    }


def _event_context(event: Mapping[str, Any]) -> dict[str, Any]:
    context: dict[str, Any] = {}

    for payload in _nested_mappings(event):
        context.update(payload)

    context.update(event)
    return context


def _nested_mappings(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    payloads: list[Mapping[str, Any]] = []

    for key in ("issue", "data", "triggerContext"):
        value = event.get(key)
        if isinstance(value, Mapping):
            nested_issue = value.get("issue")
            if isinstance(nested_issue, Mapping):
                payloads.append(nested_issue)
            payloads.append(value)

    return payloads


def _is_status_change(context: Mapping[str, Any]) -> bool:
    trigger_fields = (
        _normalize_text(value)
        for value in _texts(context, ("trigger", "webhookType", "action", "type"))
    )
    saw_trigger = False
    saw_issue_update = False

    for trigger in trigger_fields:
        saw_trigger = True
        if trigger in {"status changed", "statuschanged"}:
            return True
        if trigger in {"issue updated", "updated issue"}:
            saw_issue_update = True

    if saw_issue_update:
        return _has_status_updated_field(context)

    return not saw_trigger and _has_status_updated_field(context)


def _has_status_updated_field(context: Mapping[str, Any]) -> bool:
    updated_fields = context.get("updatedFields") or context.get("updated_fields")
    return _contains_status_field(updated_fields)


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_text(value) in {"status", "state"}

    if isinstance(value, Mapping):
        return any(
            _normalize_text(str(key)) in {"status", "state"} for key in value.keys()
        )

    if isinstance(value, list | tuple | set):
        return any(_contains_status_field(item) for item in value)

    return False


def _new_status(context: Mapping[str, Any]) -> str | None:
    new_status = _first_text(
        context,
        ("newStatus", "new_status", "status", "statusName", "stateName"),
    )
    if new_status is not None:
        return new_status

    state = context.get("state")
    if isinstance(state, Mapping):
        return _first_text(state, ("name",))

    return None


def _first_text(source: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    return next(_texts(source, keys), None)


def _texts(source: Mapping[str, Any], keys: tuple[str, ...]) -> Iterator[str]:
    for key in keys:
        value = source.get(key)
        if isinstance(value, str) and value.strip():
            yield value


def _normalize_text(value: str | None) -> str:
    if not isinstance(value, str):
        return ""

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    normalized = re.sub(r"[^a-z0-9]+", " ", spaced.lower())
    return " ".join(normalized.split())


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())
