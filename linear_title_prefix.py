"""Build Linear issue title updates for research status transitions."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a title update action when a Linear issue moves to research."""
    if not isinstance(event, Mapping):
        return None

    sources = _event_sources(event)
    if not _is_status_change_event(sources):
        return None

    new_status = _first_value(
        sources,
        ("newStatus", "new_status", "status", "statusName", "stateName"),
    )
    if new_status is None:
        new_status = _state_name(sources)

    if _normalize_status(new_status) != TARGET_STATUS:
        return None

    issue_id = _clean_string(
        _first_value(sources, ("id", "issueId", "issue_id", "identifier"))
    )
    title = _clean_string(_first_value(sources, ("title", "name")))
    if not issue_id or not title:
        return None

    if title.lower().startswith(TITLE_PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _event_sources(event: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    context = _mapping_value(event.get("triggerContext"))
    data = _mapping_value(event.get("data"))
    top_level_issue = _mapping_value(event.get("issue"))
    data_issue = _mapping_value(data.get("issue") if data else None)

    # Prefer automation context, then Linear issue payloads, while keeping the
    # root event available for flat test/webhook payloads.
    return tuple(
        source
        for source in (context, data_issue, top_level_issue, data, event)
        if source is not None
    )


def _is_status_change_event(sources: Sequence[Mapping[str, Any]]) -> bool:
    trigger_values = tuple(
        value
        for value in _values_for_keys(
            sources,
            ("trigger", "webhookType", "action", "type"),
        )
        if value is not None
    )

    if any(_is_direct_status_change(value) for value in trigger_values):
        return True

    if any(_is_issue_update(value) for value in trigger_values):
        return _updated_fields_include_status(sources)

    return False


def _is_direct_status_change(value: Any) -> bool:
    normalized = _normalize_identifier(value)
    return normalized in {"statuschanged", "statuschange"} or (
        "status" in normalized and "chang" in normalized
    )


def _is_issue_update(value: Any) -> bool:
    normalized = _normalize_identifier(value)
    return normalized in {
        "issueupdated",
        "updatedissue",
        "issueupdate",
        "updateissue",
    }


def _updated_fields_include_status(sources: Sequence[Mapping[str, Any]]) -> bool:
    updated_fields = _first_value(sources, ("updatedFields", "updated_fields"))
    if isinstance(updated_fields, str):
        fields = (updated_fields,)
    elif isinstance(updated_fields, Sequence) and not isinstance(
        updated_fields, (bytes, bytearray)
    ):
        fields = updated_fields
    else:
        return False

    return any(_normalize_identifier(field) in {"status", "state"} for field in fields)


def _state_name(sources: Sequence[Mapping[str, Any]]) -> Any:
    for source in sources:
        for key in ("state", "workflowState"):
            state = _mapping_value(source.get(key))
            if state and state.get("name") is not None:
                return state["name"]
    return None


def _first_value(sources: Sequence[Mapping[str, Any]], keys: Sequence[str]) -> Any:
    for source in sources:
        for key in keys:
            value = source.get(key)
            if value is not None:
                return value
    return None


def _values_for_keys(
    sources: Sequence[Mapping[str, Any]], keys: Sequence[str]
) -> tuple[Any, ...]:
    return tuple(
        source[key] for source in sources for key in keys if source.get(key) is not None
    )


def _mapping_value(value: Any) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None


def _clean_string(value: Any) -> str | None:
    if value is None:
        return None

    cleaned = str(value).strip()
    return cleaned or None


def _normalize_status(value: Any) -> str:
    if value is None:
        return ""

    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", str(value))
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return " ".join(text.lower().split())


def _normalize_identifier(value: Any) -> str:
    if value is None:
        return ""

    return re.sub(r"[^a-z0-9]+", "", str(value).lower())
