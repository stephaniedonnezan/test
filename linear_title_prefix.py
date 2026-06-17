"""Build Linear issue title updates for research-status automations."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


RESEARCH_STATUS = "to research"
TITLE_PREFIX = "Cursor researching"

_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflowstate",
    "workflow_state",
    "workflow state",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear issue-title update action for to-research status changes.

    The automation platform can pass either a flat ``triggerContext`` payload or
    a nested Linear webhook payload. Returning ``None`` means the event should
    not change the issue title.
    """

    if not isinstance(event, Mapping):
        return None

    mappings = list(_iter_context_mappings(event))

    if not _is_status_change_event(mappings):
        return None

    status = _find_status_name(mappings)
    if _normalize_words(status) != RESEARCH_STATUS:
        return None

    issue_id = _find_issue_id(mappings)
    title = _find_title(mappings)
    if not issue_id or not title:
        return None

    if _has_title_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _iter_context_mappings(event: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    """Yield relevant mappings from outer metadata to nested issue payloads."""

    yield event

    for key in ("triggerContext", "trigger_context", "data", "payload", "issue"):
        value = event.get(key)
        if isinstance(value, Mapping):
            yield value

    for container_key in ("triggerContext", "trigger_context", "data", "payload"):
        container = event.get(container_key)
        if not isinstance(container, Mapping):
            continue
        for nested_key in ("issue", "data"):
            nested = container.get(nested_key)
            if isinstance(nested, Mapping):
                yield nested


def _is_status_change_event(mappings: list[Mapping[str, Any]]) -> bool:
    event_names: list[str] = []
    for mapping in mappings:
        for key in ("trigger", "webhookType", "webhook_type", "action", "type"):
            value = mapping.get(key)
            if isinstance(value, str):
                event_names.append(_normalize_words(value))

    if any(name in {"status changed", "state changed", "workflow state changed"} for name in event_names):
        return True

    if any(name in {"issue updated", "updated issue", "update"} for name in event_names):
        return _updated_fields_include_status(mappings)

    return False


def _updated_fields_include_status(mappings: list[Mapping[str, Any]]) -> bool:
    for mapping in mappings:
        for key in (
            "updatedFields",
            "updated_fields",
            "changedFields",
            "changed_fields",
            "changes",
            "updatedFrom",
            "updated_from",
        ):
            value = mapping.get(key)
            if _contains_status_field(value):
                return True
    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_field_name(value) in _STATUS_FIELD_NAMES
    if isinstance(value, Mapping):
        return any(_normalize_field_name(str(key)) in _STATUS_FIELD_NAMES for key in value)
    if isinstance(value, Iterable):
        return any(_contains_status_field(item) for item in value)
    return False


def _find_status_name(mappings: list[Mapping[str, Any]]) -> str | None:
    for key in (
        "newStatus",
        "new_status",
        "newState",
        "new_state",
        "statusName",
        "status_name",
        "stateName",
        "state_name",
        "workflowStateName",
        "workflow_state_name",
    ):
        status = _first_string_value(mappings, key)
        if status:
            return status

    for key in ("status", "state", "workflowState", "workflow_state"):
        status = _first_status_value(mappings, key)
        if status:
            return status

    return None


def _find_issue_id(mappings: list[Mapping[str, Any]]) -> str | None:
    for key in ("issueId", "issue_id", "identifier", "key", "id"):
        value = _first_string_value(mappings, key)
        if value:
            return value
    return None


def _find_title(mappings: list[Mapping[str, Any]]) -> str | None:
    return _first_string_value(mappings, "title")


def _first_string_value(mappings: list[Mapping[str, Any]], key: str) -> str | None:
    for mapping in mappings:
        value = mapping.get(key)
        if isinstance(value, str):
            stripped = value.strip()
            if stripped:
                return stripped
    return None


def _first_status_value(mappings: list[Mapping[str, Any]], key: str) -> str | None:
    for mapping in mappings:
        value = mapping.get(key)
        if isinstance(value, str):
            stripped = value.strip()
            if stripped:
                return stripped
        if isinstance(value, Mapping):
            for nested_key in ("name", "label", "title"):
                nested = value.get(nested_key)
                if isinstance(nested, str) and nested.strip():
                    return nested.strip()
    return None


def _has_title_prefix(title: str) -> bool:
    return title.lower().startswith(TITLE_PREFIX.lower())


def _normalize_words(value: str | None) -> str:
    if not value:
        return ""
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    spaced = re.sub(r"[^A-Za-z0-9]+", " ", spaced)
    return re.sub(r"\s+", " ", spaced).strip().lower()


def _normalize_field_name(value: str) -> str:
    return _normalize_words(value).replace(" ", "")


def main() -> int:
    """Read an event JSON object from stdin and print the update action."""

    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
