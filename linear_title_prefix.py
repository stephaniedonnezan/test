"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update payload when a Linear issue moves to research.

    The automation payload can be either flat or nested under keys such as
    ``triggerContext``, ``data``, and ``issue``. This function keeps the public
    contract intentionally small: return a serializable update request, or
    ``None`` when no title change should be made.
    """

    if not isinstance(event, Mapping):
        return None

    payload = _flatten_event(event)

    if not _is_status_changed_event(payload):
        return None

    if _normalize_value(_status_from(payload)) != _normalize_value(TARGET_STATUS):
        return None

    issue_id = _first_string(payload, "id", "issueId", "issue_id", "identifier")
    title = _first_string(payload, "title")
    if issue_id is None or title is None:
        return None

    trimmed_title = title.strip()
    if not trimmed_title or _has_research_prefix(trimmed_title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {trimmed_title}",
    }


def _flatten_event(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common nested Linear payload layers with outer values winning."""

    flattened: dict[str, Any] = {}

    for key in ("triggerContext", "data", "issue"):
        nested = event.get(key)
        if isinstance(nested, Mapping):
            flattened.update(_flatten_event(nested))

    flattened.update(event)
    return flattened


def _is_status_changed_event(payload: Mapping[str, Any]) -> bool:
    for key in ("trigger", "webhookType", "action", "type"):
        value = payload.get(key)
        if not isinstance(value, str):
            continue

        normalized = _normalize_value(value)
        if normalized in {"status changed", "status change", "statuschanged"}:
            return True

    return False


def _status_from(payload: Mapping[str, Any]) -> str | None:
    direct_status = _first_string(payload, "newStatus", "new_status", "status")
    if direct_status is not None:
        return direct_status

    state = payload.get("state")
    if isinstance(state, Mapping):
        return _first_string(state, "name")

    return None


def _first_string(payload: Mapping[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str):
            stripped = value.strip()
            if stripped:
                return stripped

    return None


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(TITLE_PREFIX.casefold())


def _normalize_value(value: str | None) -> str | None:
    if value is None:
        return None

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    separated = re.sub(r"[_\-\s]+", " ", spaced)
    return separated.strip().casefold()
