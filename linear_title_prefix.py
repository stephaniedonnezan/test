"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
PREFIXED_TITLE = f"{TITLE_PREFIX}: "
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear issue title update when an issue enters research."""
    if not isinstance(event, Mapping):
        return None

    payload = _flatten_payload(event)
    if not _is_status_change(payload):
        return None

    if _normalize_text(_pick_first(payload, ("newStatus", "new_status", "status"))) != TARGET_STATUS:
        state = payload.get("state")
        if not isinstance(state, Mapping) or _normalize_text(state.get("name")) != TARGET_STATUS:
            return None

    issue_id = _pick_first(payload, ("id", "issueId", "issue_id", "identifier"))
    title = _pick_first(payload, ("title", "name"))
    if not isinstance(issue_id, str) or not issue_id.strip():
        return None
    if not isinstance(title, str) or not title.strip():
        return None

    stripped_title = title.strip()
    if stripped_title.lower().startswith(TITLE_PREFIX.lower()):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id.strip(),
        "title": f"{PREFIXED_TITLE}{stripped_title}",
    }


def _flatten_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common Linear wrapper shapes into one payload."""
    payload: dict[str, Any] = {}

    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        _overlay_payload(payload, trigger_context)

    _overlay_payload(payload, event)
    return payload


def _overlay_payload(payload: dict[str, Any], source: Mapping[str, Any]) -> None:
    data = source.get("data")
    if isinstance(data, Mapping):
        _overlay_payload(payload, data)

    issue = source.get("issue")
    if isinstance(issue, Mapping):
        payload.update(issue)

    payload.update(source)


def _is_status_change(payload: Mapping[str, Any]) -> bool:
    trigger = _pick_first(payload, ("trigger", "webhookType", "action", "type"))
    normalized = _normalize_text(trigger)
    return normalized in {"status changed", "statuschanged"}


def _pick_first(payload: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = payload.get(key)
        if value is not None:
            return value
    return None


def _normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value.strip())
    return re.sub(r"[\s_-]+", " ", spaced).strip().casefold()
