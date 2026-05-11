"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to research."""
    if not isinstance(event, Mapping):
        return None

    payload = _flatten_payload(event)
    if not _is_status_change(payload):
        return None

    status = _first_text(
        payload,
        ("newStatus", "new_status", "status"),
        nested=(("state", "name"), ("workflowState", "name")),
    )
    if _normalize_status(status) != TARGET_STATUS:
        return None

    issue_id = _first_text(payload, ("id", "issueId", "issue_id", "identifier"))
    title = _first_text(payload, ("title", "name"))
    if issue_id is None or title is None:
        return None

    issue_id = issue_id.strip()
    title = title.strip()
    if not issue_id or not title or _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _flatten_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge common Linear webhook and automation nesting shapes."""
    payload: dict[str, Any] = {}

    for key in ("triggerContext", "data", "issue"):
        value = event.get(key)
        if isinstance(value, Mapping):
            payload.update(_flatten_payload(value))

    # Outer values are automation metadata and should win over nested issue data.
    for key, value in event.items():
        if key not in {"triggerContext", "data", "issue"}:
            payload[key] = value

    return payload


def _is_status_change(payload: Mapping[str, Any]) -> bool:
    trigger_values = (
        payload.get("trigger"),
        payload.get("action"),
        payload.get("type"),
        payload.get("webhookType"),
    )
    normalized_triggers = {
        _normalize_token(value) for value in trigger_values if isinstance(value, str)
    }

    if normalized_triggers.intersection(
        {"statuschanged", "statuschange", "statusupdated"}
    ):
        return True

    if normalized_triggers.intersection({"issueupdated", "updatedissue"}):
        return _contains_status_field(
            payload.get("updatedFields") or payload.get("updated_fields")
        )

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_token(value) in {"status", "state", "workflowstate"}

    if isinstance(value, Mapping):
        return any(_contains_status_field(field_name) for field_name in value.keys())

    if isinstance(value, (list, tuple, set, frozenset)):
        return any(_contains_status_field(item) for item in value)

    return False


def _first_text(
    payload: Mapping[str, Any],
    keys: tuple[str, ...],
    *,
    nested: tuple[tuple[str, str], ...] = (),
) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str):
            return value

    for parent_key, child_key in nested:
        parent = payload.get(parent_key)
        if isinstance(parent, Mapping):
            value = parent.get(child_key)
            if isinstance(value, str):
                return value

    return None


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def _normalize_status(value: str | None) -> str | None:
    if value is None:
        return None

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    words = re.sub(r"[^a-zA-Z0-9]+", " ", spaced).strip().lower()
    return re.sub(r"\s+", " ", words)


def _normalize_token(value: str | None) -> str | None:
    status = _normalize_status(value)
    if status is None:
        return None

    return status.replace(" ", "")
