"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
ACTION_UPDATE_ISSUE_TITLE = "update_issue_title"

_TRIGGER_KEYS = ("trigger", "webhookType", "action", "type")
_STATUS_KEYS = ("newStatus", "new_status", "status")
_ISSUE_ID_KEYS = ("id", "issueId", "issue_id", "identifier")


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear issue-title update when an issue moves to research.

    The Cursor automation trigger payload may be flat or may wrap Linear data
    in `triggerContext`, `data.issue`, or `issue`. This function accepts those
    shapes and returns a side-effect-free action for the caller to apply.
    """

    if not isinstance(event, Mapping):
        return None

    trigger_context = _as_mapping(event.get("triggerContext"))
    data = _as_mapping(event.get("data"))
    root_issue = _as_mapping(event.get("issue"))
    trigger_issue = _as_mapping(trigger_context.get("issue"))
    data_issue = _as_mapping(data.get("issue"))

    trigger_sources = (trigger_context, event, data)
    status_sources = (trigger_context, event, data, data_issue, root_issue, trigger_issue)
    issue_sources = (data_issue, root_issue, trigger_issue, trigger_context, event, data)

    if not _is_status_change_event(trigger_sources):
        return None

    if _normalized_status(_first_status_string(status_sources)) != "to research":
        return None

    issue_id = _first_string(issue_sources, _ISSUE_ID_KEYS)
    title = _first_string(issue_sources, ("title",))
    if not issue_id or not title:
        return None

    issue_id = issue_id.strip()
    title = title.strip()
    if not issue_id or not title:
        return None

    if title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": ACTION_UPDATE_ISSUE_TITLE,
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _as_mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def _is_status_change_event(sources: tuple[Mapping[str, Any], ...]) -> bool:
    trigger = _first_string(sources, _TRIGGER_KEYS)
    return _normalized_token(trigger) in {"status changed", "status change"}


def _normalized_status(value: str | None) -> str | None:
    if value is None:
        return None
    return _normalized_token(value)


def _normalized_token(value: str | None) -> str | None:
    if value is None:
        return None

    token = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value.strip())
    token = re.sub(r"[^a-zA-Z0-9]+", " ", token)
    token = re.sub(r"\s+", " ", token).strip().lower()
    return token or None


def _first_status_string(sources: tuple[Mapping[str, Any], ...]) -> str | None:
    direct_status = _first_string(sources, _STATUS_KEYS)
    if direct_status is not None:
        return direct_status

    for source in sources:
        state = source.get("state")
        if isinstance(state, Mapping):
            name = state.get("name")
            if isinstance(name, str):
                return name

    return None


def _first_string(sources: tuple[Mapping[str, Any], ...], keys: tuple[str, ...]) -> str | None:
    for source in sources:
        for key in keys:
            value = source.get(key)
            if isinstance(value, str):
                return value

    return None
