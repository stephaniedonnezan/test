"""Build Linear issue title updates for research status changes."""

from collections.abc import Mapping
import re
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update action when an issue enters the research status."""
    if not isinstance(event, Mapping):
        return None

    payload = _flatten_event(event)
    if not _is_status_change(payload):
        return None

    status = _first_value(payload, ("newStatus", "new_status", "status"))
    if status is None:
        state = payload.get("state")
        if isinstance(state, Mapping):
            status = state.get("name")

    if _normalize(status) != TARGET_STATUS:
        return None

    issue_id = _first_value(payload, ("id", "issueId", "issue_id"))
    title = _first_value(payload, ("title", "name"))
    if not issue_id or not isinstance(title, str):
        return None

    title = title.strip()
    if not title or _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": str(issue_id),
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _flatten_event(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common Linear webhook nesting while preserving top-level metadata."""
    flattened: dict[str, Any] = {}

    for key in ("data", "issue", "triggerContext"):
        value = event.get(key)
        if isinstance(value, Mapping):
            flattened.update(_flatten_event(value))

    flattened.update(event)
    return flattened


def _is_status_change(payload: Mapping[str, Any]) -> bool:
    trigger = _first_value(payload, ("trigger", "webhookType", "action", "type"))
    return _normalize(trigger) in {"status changed", "status change", "statuschanged"}


def _first_value(payload: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = payload.get(key)
        if value is not None:
            return value
    return None


def _normalize(value: Any) -> str:
    if value is None:
        return ""
    normalized = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", str(value).strip())
    normalized = re.sub(r"[_-]+", " ", normalized.lower())
    return re.sub(r"\s+", " ", normalized).strip()


def _has_research_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())
