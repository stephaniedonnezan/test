"""Build Linear issue title updates for Cursor research automation."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"

_CAMEL_ACRONYM_BOUNDARY = re.compile(r"([A-Z]+)([A-Z][a-z])")
_CAMEL_WORD_BOUNDARY = re.compile(r"([a-z0-9])([A-Z])")
_SEPARATOR_RUN = re.compile(r"[\s_-]+")


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update when an issue moves to "to research".

    The automation payload may be flat or wrapped in triggerContext/data/issue.
    This function keeps the output side-effect-free so callers can decide how to
    execute the returned update.
    """

    if not isinstance(event, Mapping):
        return None

    details = _collect_issue_details(event)
    if not _is_status_change(details):
        return None

    if _normalize(_first_string(details, ("newStatus", "new_status", "status"))) != TARGET_STATUS:
        state = details.get("state")
        if not isinstance(state, Mapping) or _normalize(state.get("name")) != TARGET_STATUS:
            return None

    issue_id = _first_string(details, ("id", "issueId", "issue_id", "identifier"))
    title = _first_string(details, ("title",))
    if not issue_id or not title:
        return None

    title = title.strip()
    if not title or title.casefold().startswith(PREFIX.casefold()):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _collect_issue_details(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge likely Linear issue payload locations with outer metadata winning."""

    details: dict[str, Any] = {}

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        details.update(_collect_issue_details(trigger_context))

    data = event.get("data")
    if isinstance(data, Mapping):
        details.update(_collect_issue_details(data))

    issue = event.get("issue")
    if isinstance(issue, Mapping):
        details.update(_collect_issue_details(issue))

    details.update(event)
    return details


def _is_status_change(details: Mapping[str, Any]) -> bool:
    for field in ("trigger", "webhookType", "action", "type"):
        trigger = _normalize(details.get(field))
        if trigger in {"status changed", "status change"}:
            return True

    return False


def _first_string(details: Mapping[str, Any], fields: tuple[str, ...]) -> str | None:
    for field in fields:
        value = details.get(field)
        if isinstance(value, str):
            return value

    return None


def _normalize(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    value = value.strip()
    value = _CAMEL_ACRONYM_BOUNDARY.sub(r"\1 \2", value)
    value = _CAMEL_WORD_BOUNDARY.sub(r"\1 \2", value)
    value = _SEPARATOR_RUN.sub(" ", value)
    return value.casefold().strip()
