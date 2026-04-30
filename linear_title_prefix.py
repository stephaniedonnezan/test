"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title-update action when a Linear issue moves to To Research.

    The automation trigger payload can arrive either as a flat mapping or with
    issue fields nested below ``triggerContext``, ``data``, or ``issue``.
    """

    if not isinstance(event, Mapping):
        return None

    payload = _flatten_payload(event)

    if not _is_status_changed(payload):
        return None

    if _normalize(payload.get("newStatus") or payload.get("new_status") or payload.get("status") or _state_name(payload)) != "to research":
        return None

    issue_id = payload.get("id") or payload.get("issueId") or payload.get("issue_id") or payload.get("identifier")
    title = payload.get("title")

    if not isinstance(issue_id, str) or not issue_id.strip():
        return None
    if not isinstance(title, str) or not title.strip():
        return None

    clean_title = title.strip()
    if clean_title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {clean_title}",
    }


def _flatten_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}

    for key in ("triggerContext", "data", "issue"):
        value = event.get(key)
        if isinstance(value, Mapping):
            payload.update(_flatten_payload(value))

    payload.update(event)
    return payload


def _is_status_changed(payload: Mapping[str, Any]) -> bool:
    trigger_values = (
        payload.get("trigger"),
        payload.get("webhookType"),
        payload.get("action"),
        payload.get("type"),
    )

    return any(_normalize(value) == "status changed" for value in trigger_values)


def _state_name(payload: Mapping[str, Any]) -> Any:
    state = payload.get("state")
    if isinstance(state, Mapping):
        return state.get("name")
    return None


def _normalize(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    spaced = re.sub(r"[_-]+", " ", spaced)
    return re.sub(r"\s+", " ", spaced).strip().lower()
