"""Build Linear issue title updates for Cursor research automation."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


TITLE_PREFIX = "Cursor researching"
RESEARCH_STATUS = "to research"


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to research.

    The automation webhook shape has varied between flat Cursor triggerContext
    payloads and nested Linear issue update payloads. This function accepts both
    so the title-prefix decision stays in one testable place.
    """

    if not _is_linear_status_change_event(event):
        return None

    status = _extract_new_status(event)
    if _normalize_status(status) != RESEARCH_STATUS:
        return None

    issue_id = _extract_issue_id(event)
    title = _extract_title(event)
    if not issue_id or not title:
        return None

    if _has_research_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _is_linear_status_change_event(event: Mapping[str, Any]) -> bool:
    trigger_context = _as_mapping(event.get("triggerContext"))
    candidates = (event, trigger_context) if trigger_context else (event,)

    for candidate in candidates:
        trigger_type = _normalize_status(candidate.get("triggerType"))
        webhook_type = _normalize_status(candidate.get("webhookType"))
        trigger = _normalize_status(candidate.get("trigger"))
        action = _normalize_status(candidate.get("action"))
        issue_type = _normalize_status(candidate.get("type"))

        is_cursor_status_change = (
            trigger_type == "linear"
            and webhook_type == "issue"
            and trigger == "status changed"
        )
        is_linear_issue_update = issue_type == "issue" and action == "update"

        if is_cursor_status_change or is_linear_issue_update:
            return True

    return False


def _extract_new_status(event: Mapping[str, Any]) -> Any:
    trigger_context = _as_mapping(event.get("triggerContext"))

    for candidate in _compact_mappings(trigger_context, event):
        for key in ("newStatus", "status", "state", "workflowState"):
            if key in candidate:
                return _status_value(candidate[key])

        changes_status = _status_from_changes(candidate.get("changes"))
        if changes_status is not None:
            return changes_status

        updated_field_status = _status_from_updated_fields(candidate.get("updatedFields"))
        if updated_field_status is not None:
            return updated_field_status

    data = _as_mapping(event.get("data"))
    if data:
        for key in ("state", "status", "workflowState"):
            if key in data:
                return _status_value(data[key])

        changes_status = _status_from_changes(data.get("changes"))
        if changes_status is not None:
            return changes_status

    updated_from_state = _linear_updated_from_state(event)
    if updated_from_state is not None:
        return updated_from_state

    return None


def _extract_issue_id(event: Mapping[str, Any]) -> str | None:
    trigger_context = _as_mapping(event.get("triggerContext"))
    data = _as_mapping(event.get("data"))

    for candidate in _compact_mappings(trigger_context, data, event):
        issue_id = candidate.get("issueId") or candidate.get("id")
        if issue_id:
            return str(issue_id)

    return None


def _extract_title(event: Mapping[str, Any]) -> str | None:
    trigger_context = _as_mapping(event.get("triggerContext"))
    data = _as_mapping(event.get("data"))

    for candidate in _compact_mappings(trigger_context, data, event):
        title = candidate.get("title")
        if isinstance(title, str) and title.strip():
            return title

    return None


def _status_from_changes(value: Any) -> Any:
    changes = _as_mapping(value)
    if not changes:
        return None

    for key in ("status", "state", "workflowState", "stateId"):
        if key not in changes:
            continue
        change = changes[key]
        change_mapping = _as_mapping(change)
        if change_mapping:
            for status_key in ("to", "new", "after", "name", "value"):
                if status_key in change_mapping:
                    return _status_value(change_mapping[status_key])
        return _status_value(change)

    return None


def _status_from_updated_fields(value: Any) -> Any:
    if isinstance(value, Mapping):
        changed_status = _status_from_changes(value)
        if changed_status is not None:
            return changed_status

        for key in ("status", "state", "workflowState"):
            if key in value:
                return _status_value(value[key])

    if not isinstance(value, list):
        return None

    for field in value:
        field_mapping = _as_mapping(field)
        if not field_mapping:
            continue

        field_name = _normalize_status(
            field_mapping.get("field")
            or field_mapping.get("name")
            or field_mapping.get("key")
        )
        if field_name not in {"status", "state", "workflow state"}:
            continue

        for status_key in ("to", "new", "after", "value"):
            if status_key in field_mapping:
                return _status_value(field_mapping[status_key])

    return None


def _linear_updated_from_state(event: Mapping[str, Any]) -> Any:
    updated_from = _as_mapping(event.get("updatedFrom"))
    if not updated_from or "stateId" not in updated_from:
        return None

    data = _as_mapping(event.get("data"))
    if not data:
        return None

    return _status_value(data.get("state"))


def _status_value(value: Any) -> Any:
    mapping = _as_mapping(value)
    if not mapping:
        return value

    for key in ("name", "title", "status", "state", "workflowState", "value"):
        if key in mapping:
            return _status_value(mapping[key])

    return value


def _normalize_status(value: Any) -> str | None:
    value = _status_value(value)
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[_\-/]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.casefold()


def _has_research_prefix(title: str) -> bool:
    return title.lstrip().casefold().startswith(TITLE_PREFIX.casefold())


def _as_mapping(value: Any) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None


def _compact_mappings(*values: Mapping[str, Any] | None) -> tuple[Mapping[str, Any], ...]:
    return tuple(value for value in values if value)


def main() -> int:
    event = json.load(sys.stdin)
    result = build_issue_title_update(event)
    if result is not None:
        json.dump(result, sys.stdout)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
