"""Build title updates for Linear issues entering the research status."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to research.

    The Cursor automation payload is intentionally small, but Linear webhooks can
    wrap issue data in a few different shapes. This function accepts both flat
    trigger context payloads and common nested webhook payloads.
    """

    if not isinstance(event, Mapping):
        return None

    payload = _merged_payload(event)
    if not _is_status_change(payload):
        return None

    new_status = _first_text(
        payload,
        ("newStatus", "new_status", "status", "statusName", "stateName"),
    )
    if new_status is None:
        state = payload.get("state")
        if isinstance(state, Mapping):
            new_status = _text(state.get("name"))

    if _normalize_label(new_status) != _normalize_label(TARGET_STATUS):
        return None

    issue_id = _first_text(payload, ("id", "issueId", "issue_id", "identifier"))
    title = _first_text(payload, ("title", "name"))
    if not issue_id or not title:
        return None

    title = title.strip()
    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id.strip(),
        "title": f"{PREFIX}: {title}",
    }


def _merged_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten common automation and Linear issue wrappers into one payload."""

    merged: dict[str, Any] = {}

    for key in ("data", "issue", "triggerContext"):
        value = event.get(key)
        if isinstance(value, Mapping):
            if key == "data":
                issue = value.get("issue")
                if isinstance(issue, Mapping):
                    merged.update(issue)
            merged.update(value)

    issue = merged.get("issue")
    if isinstance(issue, Mapping):
        merged.update(issue)

    # Outer trigger metadata should win over nested issue fields with the same
    # names because it describes the event that caused this run.
    merged.update(event)
    return merged


def _is_status_change(payload: Mapping[str, Any]) -> bool:
    trigger_values = [
        _text(payload.get(key))
        for key in ("trigger", "webhookType", "action", "type")
        if _text(payload.get(key))
    ]
    normalized_values = {_normalize_label(value) for value in trigger_values}

    if any(value == "status changed" for value in normalized_values):
        return True

    if any(value in {"issue updated", "updated issue"} for value in normalized_values):
        updated_fields = payload.get("updatedFields")
        if isinstance(updated_fields, str):
            fields = {_normalize_label(updated_fields)}
        elif isinstance(updated_fields, (list, tuple, set)):
            fields = {_normalize_label(_text(field)) for field in updated_fields}
        else:
            fields = set()
        return bool(fields & {"status", "state"})

    return False


def _first_text(payload: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = _text(payload.get(key))
        if value:
            return value
    return None


def _text(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    return None


def _normalize_label(value: str | None) -> str:
    if not value:
        return ""

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value.strip())
    return re.sub(r"[\W_]+", " ", spaced).strip().casefold()


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(PREFIX.casefold())
