"""Build title updates for Linear issues entering the research status."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
STATUS_CHANGE_TRIGGER = "status changed"


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to research.

    The automation trigger can provide issue fields at the top level, inside a
    triggerContext object, or inside nested data/issue payloads. This function
    accepts those common shapes and returns a small action descriptor that the
    caller can translate into a Linear mutation.
    """

    if not isinstance(event, Mapping):
        return None

    issue = _flatten_issue_payload(event)

    if _normalise_text(_first_present(issue, "trigger", "webhookType", "action", "type")) != STATUS_CHANGE_TRIGGER:
        return None

    status = _first_present(issue, "newStatus", "new_status", "status")
    if status is None:
        status = _get_nested(issue, "state", "name")

    if _normalise_text(status) != TARGET_STATUS:
        return None

    issue_id = _string_value(_first_present(issue, "id", "issueId", "issue_id", "identifier"))
    title = _string_value(_first_present(issue, "title", "name"))

    if issue_id is None or title is None:
        return None

    stripped_title = title.strip()
    if not stripped_title or _normalise_text(stripped_title).startswith(_normalise_text(PREFIX)):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {stripped_title}",
    }


def _flatten_issue_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge likely Linear issue payload containers into one lookup dict."""

    merged: dict[str, Any] = {}

    for container in _candidate_containers(event):
        merged.update(container)

    # Prefer top-level trigger metadata supplied by the automation wrapper.
    for key in ("trigger", "webhookType", "action", "type", "newStatus", "new_status", "status"):
        if key in event:
            merged[key] = event[key]

    return merged


def _candidate_containers(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    containers: list[Mapping[str, Any]] = [event]

    for key in ("triggerContext", "data", "issue"):
        value = _get_nested(event, key)
        if isinstance(value, Mapping):
            containers.append(value)

    trigger_context = _get_nested(event, "triggerContext")
    if isinstance(trigger_context, Mapping):
        for key in ("data", "issue"):
            value = _get_nested(trigger_context, key)
            if isinstance(value, Mapping):
                containers.append(value)

        data = _get_nested(trigger_context, "data")
        if isinstance(data, Mapping):
            issue = _get_nested(data, "issue")
            if isinstance(issue, Mapping):
                containers.append(issue)

    data = _get_nested(event, "data")
    if isinstance(data, Mapping):
        issue = _get_nested(data, "issue")
        if isinstance(issue, Mapping):
            containers.append(issue)

    return containers


def _first_present(data: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in data:
            return data[key]
    return None


def _get_nested(data: Mapping[str, Any], *keys: str) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, Mapping) or key not in current:
            return None
        current = current[key]
    return current


def _normalise_text(value: Any) -> str:
    text = _string_value(value)
    if text is None:
        return ""

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text.strip())
    return re.sub(r"[\W_]+", " ", spaced).strip().casefold()


def _string_value(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    return None
