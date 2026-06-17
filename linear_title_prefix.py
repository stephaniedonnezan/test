"""Build Linear issue title updates for research status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_KEYS = {
    "status",
    "statusid",
    "state",
    "stateid",
    "workflowstate",
    "workflowstateid",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to To Research."""
    if not isinstance(event, Mapping):
        return None

    sources = _sources(event)
    if not _is_status_change_event(sources):
        return None

    new_status = _new_status(sources)
    if _normalize_words(new_status) != TARGET_STATUS:
        return None

    issue_id = _issue_id(sources)
    title = _issue_title(sources)
    if not issue_id or not title or _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _sources(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return likely event and issue containers from most to least specific."""
    sources: list[Mapping[str, Any]] = []

    trigger_context = _mapping_field(event, "triggerContext")
    if trigger_context:
        sources.append(trigger_context)

    data = _mapping_field(event, "data")
    issue = _mapping_field(event, "issue")
    data_issue = _mapping_field(data, "issue") if data else None
    payload = _mapping_field(event, "payload")
    payload_issue = _mapping_field(payload, "issue") if payload else None

    for candidate in (data_issue, issue, payload_issue, data, payload, event):
        if candidate and candidate not in sources:
            sources.append(candidate)

    return sources


def _is_status_change_event(sources: list[Mapping[str, Any]]) -> bool:
    descriptors = []
    for source in sources:
        descriptors.extend(
            _text_field(source, name)
            for name in ("trigger", "webhookType", "webhook_type", "action", "type", "event", "eventType")
            if _text_field(source, name)
        )

    normalized = {_normalize_words(descriptor) for descriptor in descriptors}
    if any(_is_direct_status_change(descriptor) for descriptor in normalized):
        return True

    is_update = bool(
        normalized
        & {
            "update",
            "updated",
            "issue update",
            "issue updated",
            "updated issue",
        }
    )
    return is_update and _changed_status_field(sources)


def _is_direct_status_change(descriptor: str) -> bool:
    return descriptor in {
        "status changed",
        "state changed",
        "workflow state changed",
    } or descriptor.endswith(" status changed")


def _changed_status_field(sources: list[Mapping[str, Any]]) -> bool:
    for source in sources:
        for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
            if _contains_status_field(_field(source, key)):
                return True

        for key in ("changes", "updatedFrom", "updated_from", "previousValues", "previous_values"):
            value = _field(source, key)
            if isinstance(value, Mapping) and any(_is_status_field_name(field) for field in value):
                return True
            if _contains_status_field(value):
                return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field_name(value)
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if _is_status_field_name(key) or _contains_status_field(nested):
                return True
    if isinstance(value, (list, tuple, set)):
        for item in value:
            if _contains_status_field(item):
                return True
    return False


def _is_status_field_name(value: Any) -> bool:
    if not isinstance(value, str):
        return False

    key = _normalize_key(value)
    return key in _STATUS_FIELD_KEYS or _normalize_words(value) in {
        "workflow state",
        "workflow state id",
    }


def _new_status(sources: list[Mapping[str, Any]]) -> str | None:
    for field_name in (
        "newStatus",
        "new_status",
        "toStatus",
        "to_status",
        "newState",
        "new_state",
        "statusName",
        "status_name",
        "stateName",
        "state_name",
        "workflowStateName",
        "workflow_state_name",
    ):
        value = _first_text(sources, field_name)
        if value:
            return value

    for source in sources:
        for field_name in ("status", "state", "workflowState", "workflow_state"):
            value = _field(source, field_name)
            text = _text_value(value)
            if text:
                return text

    return None


def _issue_id(sources: list[Mapping[str, Any]]) -> str | None:
    for field_name in ("identifier", "key", "issueId", "issue_id", "id"):
        value = _first_text(sources, field_name)
        if value:
            return value
    return None


def _issue_title(sources: list[Mapping[str, Any]]) -> str | None:
    return _first_text(sources, "title")


def _first_text(sources: list[Mapping[str, Any]], field_name: str) -> str | None:
    for source in sources:
        text = _text_value(_field(source, field_name))
        if text:
            return text
    return None


def _text_value(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    if isinstance(value, Mapping):
        for field_name in ("name", "title", "label"):
            text = _text_value(_field(value, field_name))
            if text:
                return text
    return None


def _mapping_field(mapping: Mapping[str, Any] | None, field_name: str) -> Mapping[str, Any] | None:
    value = _field(mapping, field_name) if mapping else None
    return value if isinstance(value, Mapping) else None


def _text_field(mapping: Mapping[str, Any], field_name: str) -> str | None:
    return _text_value(_field(mapping, field_name))


def _field(mapping: Mapping[str, Any] | None, field_name: str) -> Any:
    if not isinstance(mapping, Mapping):
        return None

    if field_name in mapping:
        return mapping[field_name]

    normalized = _normalize_key(field_name)
    for key, value in mapping.items():
        if isinstance(key, str) and _normalize_key(key) == normalized:
            return value

    return None


def _has_prefix(title: str) -> bool:
    return title.lstrip().lower().startswith(PREFIX.lower())


def _normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", _normalize_words(value))


def _normalize_words(value: Any) -> str:
    if not isinstance(value, str):
        return ""

    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", value)
    return re.sub(r"\s+", " ", re.sub(r"[^A-Za-z0-9]+", " ", spaced).strip()).lower()


def main() -> int:
    event = json.load(sys.stdin)
    result = build_issue_title_update(event)
    if result:
        print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
