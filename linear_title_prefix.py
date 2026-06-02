"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_CHANGE_TRIGGERS = {"status changed", "status change"}
_UPDATE_ACTIONS = {"update", "issue updated", "updated issue"}
_STATUS_FIELD_NAMES = {"status", "state", "workflow state", "workflowstate"}
_UPDATED_FIELD_KEYS = {
    "updatedFields",
    "updated_fields",
    "changedFields",
    "changed_fields",
}
_UPDATED_FROM_KEYS = {"updatedFrom", "updated_from", "changes", "changed"}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return an issue-title update action when a Linear issue moves to research."""
    if not isinstance(event, Mapping):
        return None

    maps = _candidate_maps(event)
    if not _is_status_change_event(event, maps):
        return None

    status = _extract_status(maps)
    if _normalize_text(status) != TARGET_STATUS:
        return None

    issue_id = _extract_first_text(
        maps,
        ("id", "issueId", "issue_id", "identifier", "uuid"),
    )
    title = _extract_first_text(maps, ("title", "name"))
    if not issue_id or not title:
        return None

    if title.casefold().startswith(PREFIX.casefold()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _candidate_maps(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return likely payload maps from most to least issue-specific."""
    candidates: list[Mapping[str, Any]] = []

    trigger_context = _mapping_at(event, "triggerContext")
    data = _mapping_at(event, "data")
    issue = _mapping_at(event, "issue")

    nested_maps = [
        _mapping_at(trigger_context, "issue"),
        _mapping_at(trigger_context, "data"),
        _mapping_at(data, "issue"),
        issue,
        data,
        trigger_context,
        event,
    ]

    seen: set[int] = set()
    for candidate in nested_maps:
        if candidate is None:
            continue
        marker = id(candidate)
        if marker in seen:
            continue
        seen.add(marker)
        candidates.append(candidate)

    return candidates


def _mapping_at(mapping: Mapping[str, Any] | None, key: str) -> Mapping[str, Any] | None:
    if not isinstance(mapping, Mapping):
        return None

    value = mapping.get(key)
    if isinstance(value, Mapping):
        return value

    return None


def _is_status_change_event(
    event: Mapping[str, Any],
    maps: list[Mapping[str, Any]],
) -> bool:
    trigger_values = _extract_values(
        maps,
        ("trigger", "event", "eventType", "webhookType", "action", "type"),
    )
    normalized_values = {_normalize_text(value) for value in trigger_values}

    if normalized_values & _STATUS_CHANGE_TRIGGERS:
        return True

    if normalized_values & _UPDATE_ACTIONS:
        return _updated_fields_include_status(event)

    return False


def _extract_status(maps: list[Mapping[str, Any]]) -> str | None:
    explicit_status = _extract_first_text(
        maps,
        (
            "newStatus",
            "new_status",
            "newState",
            "new_state",
            "newWorkflowState",
            "new_workflow_state",
        ),
    )
    if explicit_status:
        return explicit_status

    return _extract_first_text(
        maps,
        ("status", "state", "workflowState", "workflow_state"),
    )


def _extract_values(maps: list[Mapping[str, Any]], keys: tuple[str, ...]) -> list[str]:
    values: list[str] = []
    for mapping in maps:
        for key in keys:
            text = _to_text(mapping.get(key))
            if text:
                values.append(text)
    return values


def _extract_first_text(
    maps: list[Mapping[str, Any]],
    keys: tuple[str, ...],
) -> str | None:
    for mapping in maps:
        for key in keys:
            text = _to_text(mapping.get(key))
            if text:
                return text
    return None


def _to_text(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "id", "identifier"):
            text = _to_text(value.get(key))
            if text:
                return text

    return None


def _updated_fields_include_status(event: Mapping[str, Any]) -> bool:
    for mapping in _walk_mappings(event):
        for key in _UPDATED_FIELD_KEYS:
            if key in mapping and _field_collection_has_status(mapping[key]):
                return True

        for key in _UPDATED_FROM_KEYS:
            if key in mapping and _field_collection_has_status(mapping[key]):
                return True

    return False


def _field_collection_has_status(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_text(value) in _STATUS_FIELD_NAMES

    if isinstance(value, Mapping):
        for key, item in value.items():
            if _normalize_text(str(key)) in _STATUS_FIELD_NAMES:
                return True

            if key in ("field", "fieldName", "name") and _field_collection_has_status(item):
                return True

            if isinstance(item, (Mapping, list, tuple)) and _field_collection_has_status(item):
                return True

        return False

    if isinstance(value, (list, tuple)):
        return any(_field_collection_has_status(item) for item in value)

    return False


def _walk_mappings(value: Any) -> list[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        mappings = [value]
        for item in value.values():
            mappings.extend(_walk_mappings(item))
        return mappings

    if isinstance(value, list):
        mappings: list[Mapping[str, Any]] = []
        for item in value:
            mappings.extend(_walk_mappings(item))
        return mappings

    return []


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None

    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value.strip())
    lowered = re.sub(r"[^0-9A-Za-z]+", " ", spaced).casefold()
    normalized = re.sub(r"\s+", " ", lowered).strip()
    return normalized or None


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError as error:
        print(f"Invalid JSON payload: {error}", file=sys.stderr)
        return 2

    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
