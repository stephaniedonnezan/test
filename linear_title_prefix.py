"""Build Linear issue title updates for research status transitions."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
PREFIXED_TITLE_FORMAT = f"{TITLE_PREFIX}: {{title}}"
UPDATE_ACTION = "update_issue_title"
RESEARCH_STATUS = "to research"
STATUS_CHANGED_TRIGGER = "status changed"


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to To Research."""

    if not isinstance(event, Mapping):
        return None

    payload = _issue_payload(event)
    context = _trigger_context(event)

    if not _is_status_changed(event, context, payload):
        return None

    if _normalize_text(_first_text((context, payload), "newStatus", "new_status", "status")) != RESEARCH_STATUS:
        state = _first_mapping((context, payload), "state")
        if _normalize_text(_mapping_text(state, "name")) != RESEARCH_STATUS:
            return None

    issue_id = _first_text((payload, context), "id", "issueId", "issue_id", "identifier")
    title = _first_text((payload, context), "title")
    if not issue_id or not title:
        return None

    clean_title = title.strip()
    if not clean_title or _has_research_prefix(clean_title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id.strip(),
        "title": PREFIXED_TITLE_FORMAT.format(title=clean_title),
    }


def _trigger_context(event: Mapping[str, Any]) -> Mapping[str, Any]:
    context = event.get("triggerContext")
    return context if isinstance(context, Mapping) else {}


def _issue_payload(event: Mapping[str, Any]) -> Mapping[str, Any]:
    data = event.get("data")
    if isinstance(data, Mapping):
        issue = data.get("issue")
        if isinstance(issue, Mapping):
            return issue
        return data

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        return issue

    context = _trigger_context(event)
    context_issue = context.get("issue")
    if isinstance(context_issue, Mapping):
        return context_issue

    return event


def _is_status_changed(
    event: Mapping[str, Any],
    context: Mapping[str, Any],
    payload: Mapping[str, Any],
) -> bool:
    trigger = _first_text(
        (event, context, payload),
        "trigger",
        "webhookType",
        "action",
        "type",
    )
    return _normalize_text(trigger) == STATUS_CHANGED_TRIGGER


def _first_text(sources: tuple[Mapping[str, Any], ...], *keys: str) -> str | None:
    for source in sources:
        if not isinstance(source, Mapping):
            continue
        for key in keys:
            value = source.get(key)
            if isinstance(value, str):
                stripped_value = value.strip()
                if stripped_value:
                    return stripped_value
    return None


def _first_mapping(sources: tuple[Mapping[str, Any], ...], *keys: str) -> Mapping[str, Any]:
    for source in sources:
        if not isinstance(source, Mapping):
            continue
        for key in keys:
            value = source.get(key)
            if isinstance(value, Mapping):
                return value
    return {}


def _mapping_text(source: Mapping[str, Any], key: str) -> str | None:
    value = source.get(key)
    if isinstance(value, str):
        stripped_value = value.strip()
        if stripped_value:
            return stripped_value
    return None


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value.strip())
    normalized = re.sub(r"[^a-z0-9]+", " ", spaced.lower()).strip()
    return normalized or None


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())
