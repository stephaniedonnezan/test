"""Build Linear issue-title updates for Cursor research automation."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
TARGET_STATUS = "to research"


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return the title-update action for Linear issues moved to research.

    The automation payloads seen by Cursor can be flat, wrapped in
    ``triggerContext``, or shaped like a Linear webhook with issue data nested
    under ``data`` or ``issue``. This function keeps the behavior independent of
    that envelope and returns ``None`` when no title change is needed.
    """

    if not isinstance(event, Mapping):
        return None

    layers = list(_event_layers(event))
    if not _is_status_change(layers):
        return None

    status = _first_text(
        layers,
        (
            "newStatus",
            "new_status",
            "status",
            "status.name",
            "state.name",
            "state",
        ),
    )
    if _normalize_text(status) != TARGET_STATUS:
        return None

    issue_id = _first_text(layers, ("id", "issueId", "issue_id", "identifier"))
    title = _first_text(layers, ("title",))
    if not issue_id or not title:
        return None

    if title.casefold().startswith(TITLE_PREFIX.casefold()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _event_layers(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield payload layers from broad envelope fields to issue-specific data."""

    yield event

    trigger_context = _mapping_at(event, "triggerContext")
    data = _mapping_at(event, "data")
    issue = _mapping_at(event, "issue")

    if trigger_context:
        yield trigger_context
    if data:
        yield data
    if issue:
        yield issue

    trigger_context_data = _mapping_at(trigger_context, "data") if trigger_context else None
    trigger_context_issue = _mapping_at(trigger_context, "issue") if trigger_context else None
    data_issue = _mapping_at(data, "issue") if data else None

    if trigger_context_data:
        yield trigger_context_data
    if trigger_context_issue:
        yield trigger_context_issue
    if data_issue:
        yield data_issue

    if trigger_context_data:
        trigger_context_data_issue = _mapping_at(trigger_context_data, "issue")
        if trigger_context_data_issue:
            yield trigger_context_data_issue


def _is_status_change(layers: list[Mapping[str, Any]]) -> bool:
    trigger_fields = ("trigger", "webhookType", "action", "type")
    trigger_values = {
        _normalize_text(value)
        for layer in layers
        for field in trigger_fields
        if (value := _value_at(layer, field)) is not None
    }

    if trigger_values & {"status changed", "status change", "state changed", "state change"}:
        return True

    if trigger_values & {"issue updated", "issue update", "updated", "update"}:
        return _updated_fields_include_status(layers)

    return False


def _updated_fields_include_status(layers: list[Mapping[str, Any]]) -> bool:
    for layer in layers:
        for field in ("updatedFields", "updated_fields"):
            value = _value_at(layer, field)
            if _field_names_include_status(value):
                return True

        for field in ("updatedFrom", "updated_from", "changes"):
            value = _value_at(layer, field)
            if isinstance(value, Mapping):
                if _field_names_include_status(value.keys()):
                    return True

    return False


def _field_names_include_status(value: Any) -> bool:
    if isinstance(value, str):
        field_names: Iterable[Any] = (value,)
    elif isinstance(value, Mapping):
        field_names = value.keys()
    elif isinstance(value, Iterable):
        field_names = value
    else:
        return False

    status_fields = {"status", "state", "status id", "state id"}
    return any(_normalize_text(field_name) in status_fields for field_name in field_names)


def _first_text(layers: list[Mapping[str, Any]], fields: Iterable[str]) -> str | None:
    for layer in reversed(layers):
        for field in fields:
            value = _value_at(layer, field)
            if isinstance(value, str):
                cleaned = value.strip()
                if cleaned:
                    return cleaned
    return None


def _mapping_at(mapping: Mapping[str, Any] | None, key: str) -> Mapping[str, Any] | None:
    if not mapping:
        return None

    value = mapping.get(key)
    return value if isinstance(value, Mapping) else None


def _value_at(mapping: Mapping[str, Any], path: str) -> Any:
    value: Any = mapping
    for part in path.split("."):
        if not isinstance(value, Mapping):
            return None
        value = value.get(part)
    return value


def _normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    with_spaces = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value.strip())
    normalized = re.sub(r"[^a-zA-Z0-9]+", " ", with_spaces).casefold()
    return " ".join(normalized.split())
