"""Helpers for preparing Linear issue title updates from automation events."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return an issue-title update action for Linear issues moved to research.

    The automation payloads can arrive either as a flat issue dictionary or with
    the issue fields nested under keys such as ``triggerContext``, ``data``, or
    ``issue``. This function keeps the side-effect-free decision logic in one
    place so the caller can perform the actual Linear update.
    """

    if not isinstance(event, Mapping):
        return None

    payload = _combined_payload(event)
    if not _is_status_change_to_research(payload):
        return None

    issue_id = _first_string(
        payload,
        "id",
        "issueId",
        "issue_id",
        "identifier",
    )
    title = _first_string(payload, "title", "name")
    if not issue_id or not title:
        return None

    stripped_title = title.strip()
    if _has_research_prefix(stripped_title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {stripped_title}",
    }


def _combined_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key in ("issue", "data", "triggerContext"):
        value = event.get(key)
        if isinstance(value, Mapping):
            payload.update(value)

            nested_issue = value.get("issue")
            if isinstance(nested_issue, Mapping):
                payload.update(nested_issue)

    payload.update(event)
    return payload


def _is_status_change_to_research(payload: Mapping[str, Any]) -> bool:
    if not _looks_like_status_change(payload):
        return False

    status = _first_string(payload, "newStatus", "new_status", "status")
    if status is None:
        state = payload.get("state") or payload.get("workflowState")
        if isinstance(state, Mapping):
            status = _first_string(state, "name")

    return _normalize_words(status) == TARGET_STATUS


def _looks_like_status_change(payload: Mapping[str, Any]) -> bool:
    for key in ("trigger", "webhookType", "action", "type"):
        value = _normalize_words(payload.get(key))
        if value in {"status changed", "status change", "status updated"}:
            return True

    updated_fields = payload.get("updatedFields")
    if isinstance(updated_fields, str):
        updated_fields = [updated_fields]

    if isinstance(updated_fields, list):
        normalized_fields = {_normalize_words(field) for field in updated_fields}
        if normalized_fields & {"status", "state", "workflow state"}:
            event_type = _normalize_words(payload.get("type") or payload.get("action"))
            if event_type in {"issue updated", "updated issue", "update issue"}:
                return True

    return False


def _first_string(payload: Mapping[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value

    return None


def _has_research_prefix(title: str) -> bool:
    return title.casefold().startswith(TITLE_PREFIX.casefold())


def _normalize_words(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    with_separators = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", value)
    words = re.sub(r"[^A-Za-z0-9]+", " ", with_separators).strip().lower()
    return re.sub(r"\s+", " ", words)
