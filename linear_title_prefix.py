"""Build Linear issue title updates for research status transitions."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any


RESEARCH_PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update when an issue moves to "to research"."""
    if not isinstance(event, Mapping):
        return None

    context = _merged_context(event)
    if not _is_status_change(context):
        return None

    status = _extract_status(context)
    if _normalize_text(status) != _normalize_text(RESEARCH_STATUS):
        return None

    issue_id = _string_value(_first_present(context, ("issueId", "issue_id", "id", "identifier")))
    title = _string_value(_first_present(context, ("title", "name")))
    if not issue_id or not title:
        return None

    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{RESEARCH_PREFIX}: {title}",
    }


def handle_issue_status_changed(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Compatibility alias for automation entrypoints."""
    return build_issue_title_update(event)


def _merged_context(event: Mapping[str, Any]) -> dict[str, Any]:
    """Flatten common automation and Linear webhook nesting into one context."""
    context: dict[str, Any] = {}

    def merge_mapping(value: Any) -> None:
        if isinstance(value, Mapping):
            context.update(value)

    merge_mapping(event.get("triggerContext"))
    merge_mapping(event.get("data"))

    data = event.get("data")
    if isinstance(data, Mapping):
        merge_mapping(data.get("issue"))

    merge_mapping(event.get("issue"))
    context.update(event)
    return context


def _is_status_change(context: Mapping[str, Any]) -> bool:
    for key in ("trigger", "action", "type", "webhookType"):
        normalized = _normalize_text(context.get(key))
        if normalized in {"status changed", "status change", "statuschanged", "state changed", "state change"}:
            return True

    updated_fields = context.get("updatedFields") or context.get("updated_fields")
    if _field_list_contains(updated_fields, {"status", "state", "workflowstate", "workflow state"}):
        normalized_event = _normalize_text(_first_present(context, ("action", "type", "webhookType", "trigger")))
        return normalized_event in {"issue updated", "updated issue", "issue", "update"}

    return False


def _extract_status(context: Mapping[str, Any]) -> Any:
    direct_status = _first_present(context, ("newStatus", "new_status", "status"))
    if direct_status is not None:
        return direct_status

    for key in ("state", "workflowState"):
        value = context.get(key)
        if isinstance(value, Mapping):
            status_name = _first_present(value, ("name", "title"))
            if status_name is not None:
                return status_name
        elif value is not None:
            return value

    return None


def _first_present(mapping: Mapping[str, Any], keys: Sequence[str]) -> Any:
    for key in keys:
        if key in mapping and mapping[key] is not None:
            return mapping[key]
    return None


def _string_value(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _has_research_prefix(title: str) -> bool:
    return title.strip().casefold().startswith(RESEARCH_PREFIX.casefold())


def _field_list_contains(value: Any, targets: set[str]) -> bool:
    if isinstance(value, str):
        fields = [value]
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        fields = list(value)
    else:
        return False

    return any(_normalize_text(field) in targets for field in fields)


def _normalize_text(value: Any) -> str | None:
    text = _string_value(value)
    if text is None:
        return None

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    normalized = re.sub(r"[^a-zA-Z0-9]+", " ", spaced).strip().casefold()
    return re.sub(r"\s+", " ", normalized)
