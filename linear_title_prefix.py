"""Build Linear issue title updates for Cursor research status transitions."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_DIRECT_STATUS_CHANGE_EVENTS = {
    "status changed",
    "status change",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
}
_GENERIC_UPDATE_EVENTS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}
_TRIGGER_KEYS = {"trigger", "webhooktype", "webhook_type", "action", "type"}
_STATUS_KEYS = {"status", "state", "workflowstate", "workflow_state"}
_EXPLICIT_NEW_STATUS_KEYS = {
    "newstatus",
    "new_status",
    "tostatus",
    "to_status",
    "newstate",
    "new_state",
    "tostate",
    "to_state",
    "newworkflowstate",
    "new_workflow_state",
    "toworkflowstate",
    "to_workflow_state",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return the title update action for a Linear issue entering To Research.

    The function is intentionally side-effect free so automation runners can
    decide how to apply the returned action.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    status = _extract_new_status(event)
    if _normalize_value(status) != TARGET_STATUS:
        return None

    issue = _extract_issue(event)
    if issue is None:
        return None

    issue_id, title = issue
    if _already_prefixed(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    trigger_values = [
        _normalize_value(value)
        for mapping in _walk_mappings(event)
        for key, value in mapping.items()
        if _normalize_key(key) in _TRIGGER_KEYS and isinstance(value, str)
    ]

    if any(value in _DIRECT_STATUS_CHANGE_EVENTS for value in trigger_values):
        return True

    return any(value in _GENERIC_UPDATE_EVENTS for value in trigger_values) and _has_status_field_change(
        event
    )


def _has_status_field_change(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized_key = _normalize_key(key)
            if normalized_key in {
                "updatedfields",
                "updated_fields",
                "changedfields",
                "changed_fields",
            }:
                if _contains_status_field(child):
                    return True
            if normalized_key in {"changes", "updatedfrom", "updated_from"}:
                if _change_payload_mentions_status(child):
                    return True
            if _has_status_field_change(child):
                return True
    elif isinstance(value, list):
        return any(_has_status_field_change(item) for item in value)
    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_key(value) in _STATUS_KEYS
    if isinstance(value, Mapping):
        return any(
            _normalize_key(key) in _STATUS_KEYS
            or (
                _normalize_key(key) in {"field", "name", "key"}
                and _normalize_key(child) in _STATUS_KEYS
            )
            or _contains_status_field(child)
            for key, child in value.items()
        )
    if isinstance(value, list):
        return any(_contains_status_field(item) for item in value)
    return False


def _change_payload_mentions_status(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(
            _normalize_key(key) in _STATUS_KEYS or _contains_status_field(child)
            for key, child in value.items()
        )
    return _contains_status_field(value)


def _extract_new_status(event: Mapping[str, Any]) -> str | None:
    for mapping in _walk_mappings(event):
        for key, value in mapping.items():
            if _normalize_key(key) in _EXPLICIT_NEW_STATUS_KEYS:
                status = _coerce_name(value)
                if status:
                    return status

    status_from_changes = _extract_status_from_change_payloads(event)
    if status_from_changes:
        return status_from_changes

    for mapping in _issue_contexts(event):
        for key in ("workflowState", "workflow_state", "state", "status"):
            if key in mapping:
                status = _coerce_name(mapping[key])
                if status:
                    return status

    return None


def _extract_status_from_change_payloads(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized_key = _normalize_key(key)
            if normalized_key in {"changes", "updatedfrom", "updated_from"}:
                status = _status_from_change_payload(child)
                if status:
                    return status
            status = _extract_status_from_change_payloads(child)
            if status:
                return status
    elif isinstance(value, list):
        for item in value:
            status = _extract_status_from_change_payloads(item)
            if status:
                return status
    return None


def _status_from_change_payload(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if _normalize_key(key) in _STATUS_KEYS:
                status = _status_from_change_value(child)
                if status:
                    return status
        for child in value.values():
            status = _status_from_change_payload(child)
            if status:
                return status
    elif isinstance(value, list):
        for item in value:
            status = _status_from_change_payload(item)
            if status:
                return status
    return None


def _status_from_change_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key in ("to", "toValue", "to_value", "after", "new", "newValue", "new_value"):
            if key in value:
                status = _coerce_name(value[key])
                if status:
                    return status
        return _coerce_name(value)
    return _coerce_name(value)


def _extract_issue(event: Mapping[str, Any]) -> tuple[str, str] | None:
    for mapping in _issue_contexts(event):
        issue_id = _first_string(mapping, ("issueId", "issue_id", "id", "identifier", "key"))
        title = _first_string(mapping, ("title", "name"))
        if issue_id and title:
            return issue_id.strip(), title.strip()
    return None


def _issue_contexts(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    contexts: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and not any(value is existing for existing in contexts):
            contexts.append(value)

    if isinstance(event.get("automation_trigger_info"), Mapping):
        trigger_info = event["automation_trigger_info"]
        if isinstance(trigger_info.get("triggerContext"), Mapping):
            add(trigger_info["triggerContext"])

    if isinstance(event.get("triggerContext"), Mapping):
        add(event["triggerContext"])

    if isinstance(event.get("data"), Mapping):
        data = event["data"]
        if isinstance(data.get("issue"), Mapping):
            add(data["issue"])
        add(data)

    if isinstance(event.get("issue"), Mapping):
        add(event["issue"])

    add(event)

    for mapping in _walk_mappings(event):
        if mapping not in contexts and _first_string(mapping, ("title", "name")):
            contexts.append(mapping)

    return contexts


def _walk_mappings(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for child in value.values():
            yield from _walk_mappings(child)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_mappings(item)


def _first_string(mapping: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _coerce_name(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        for key in ("name", "title", "label"):
            nested = value.get(key)
            if isinstance(nested, str) and nested.strip():
                return nested
    return None


def _already_prefixed(title: str) -> bool:
    return title.strip().lower().startswith(PREFIX.lower())


def _normalize_key(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _normalize_value(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    spaced = re.sub(r"[^A-Za-z0-9]+", " ", spaced)
    return re.sub(r"\s+", " ", spaced).strip().lower()


def main() -> int:
    event = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(event), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
