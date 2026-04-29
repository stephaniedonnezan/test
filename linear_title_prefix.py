"""Build Linear issue title updates for Cursor research automation."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to To Research."""
    if not isinstance(event, Mapping):
        return None

    payload = _payload(event)
    trigger = (
        event.get("trigger")
        or payload.get("trigger")
        or event.get("action")
        or payload.get("action")
    )
    if _normalise(trigger) != "statuschanged":
        return None

    status = (
        payload.get("newStatus")
        or payload.get("new_status")
        or payload.get("status")
        or _state_name(payload)
    )
    if _normalise(status) != "toresearch":
        return None

    issue_id = payload.get("id") or payload.get("issueId") or payload.get("issue_id")
    title = payload.get("title")
    if not isinstance(issue_id, str) or not isinstance(title, str):
        return None

    title = title.strip()
    if not issue_id.strip() or not title or title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _payload(event: Mapping[str, Any]) -> Mapping[str, Any]:
    trigger_context = event.get("triggerContext")
    if isinstance(trigger_context, Mapping):
        return trigger_context
    data = event.get("data")
    if isinstance(data, Mapping):
        return data
    return event


def _state_name(payload: Mapping[str, Any]) -> Any:
    state = payload.get("state")
    if isinstance(state, Mapping):
        return state.get("name")
    return None


def _normalise(value: Any) -> str:
    if value is None:
        return ""
    return "".join(character for character in str(value).lower() if character.isalnum())
