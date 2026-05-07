"""Build title updates for Linear issues that move into research."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"
UPDATE_ACTION = "update_issue_title"


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action for Linear issues moved to To Research.

    The Cursor automation payload includes the useful issue fields under
    ``triggerContext``. Linear webhooks and tests may pass flatter payloads, so
    this function accepts both shapes and ignores payloads that do not clearly
    represent a status change into the target status.
    """

    if not isinstance(event, Mapping):
        return None

    payload = _merge_payload_context(event)
    if not _is_status_change(payload):
        return None

    new_status = _first_string(payload, "newStatus", "new_status", "status")
    if not new_status:
        state = payload.get("state")
        if isinstance(state, Mapping):
            new_status = _first_string(state, "name")

    if _normalize_phrase(new_status) != TARGET_STATUS:
        return None

    issue_id = _first_string(payload, "id", "issueId", "issue_id", "identifier")
    title = _first_string(payload, "title", "name")
    if not issue_id or not title:
        return None

    stripped_title = title.strip()
    if _has_title_prefix(stripped_title):
        return None

    return {
        "action": UPDATE_ACTION,
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {stripped_title}",
    }


def _merge_payload_context(event: Mapping[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}

    for key in ("data", "issue", "triggerContext"):
        value = event.get(key)
        if isinstance(value, Mapping):
            payload.update(value)

    payload.update(event)
    for key in ("data", "issue", "triggerContext"):
        payload.pop(key, None)

    return payload


def _is_status_change(payload: Mapping[str, Any]) -> bool:
    trigger = _first_string(payload, "trigger", "action", "type")
    if _normalize_phrase(trigger) == "status changed":
        return True

    updated_fields = payload.get("updatedFields")
    if isinstance(updated_fields, str):
        fields = {_normalize_phrase(updated_fields)}
    elif isinstance(updated_fields, list):
        fields = {_normalize_phrase(value) for value in updated_fields}
    else:
        fields = set()

    state_changed = bool(fields & {"status", "state", "state name"})
    issue_updated = _normalize_phrase(trigger) in {"issue updated", "update", "updated"}
    return issue_updated and state_changed


def _first_string(payload: Mapping[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _normalize_phrase(value: object) -> str:
    if not isinstance(value, str):
        return ""

    with_word_boundaries = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    words = re.sub(r"[^a-zA-Z0-9]+", " ", with_word_boundaries).strip()
    return re.sub(r"\s+", " ", words).casefold()


def _has_title_prefix(title: str) -> bool:
    return title.casefold().startswith(TITLE_PREFIX.casefold())
