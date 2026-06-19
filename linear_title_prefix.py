"""Build Linear issue title updates for research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {
    "status",
    "state",
    "workflow state",
    "workflow status",
    "workflowstate",
}
_DIRECT_STATUS_CHANGE_EVENTS = {
    "status changed",
    "state changed",
    "workflow state changed",
    "status change",
    "state change",
}
_GENERIC_UPDATE_EVENTS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}
_EXPLICIT_NEW_STATUS_KEYS = (
    "newStatus",
    "new_status",
    "newState",
    "new_state",
    "newWorkflowState",
    "new_workflow_state",
    "newWorkflowStatus",
    "new_workflow_status",
)
_CURRENT_STATUS_KEYS = (
    "status",
    "state",
    "workflowState",
    "workflow_state",
    "workflowStatus",
    "workflow_status",
)
_ISSUE_ID_KEYS = ("issueId", "issue_id", "id", "identifier", "key")
_TITLE_KEYS = ("title", "name", "summary")
_MARKER_KEYS = ("trigger", "webhookType", "webhook_type", "action", "type", "eventType")


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear issue-title update action for research status changes.

    The function accepts both the flat Cursor automation trigger context shape
    and nested Linear webhook payloads. It returns ``None`` when the payload is
    not a status change into "to research" or when the title is already marked.
    """

    if not isinstance(event, Mapping):
        return None

    if not _is_status_change_event(event):
        return None

    new_status = _find_new_status(event)
    if _normalize_words(new_status) != TARGET_STATUS:
        return None

    issue_id = _find_issue_value(event, _ISSUE_ID_KEYS)
    title = _find_issue_value(event, _TITLE_KEYS)
    if issue_id is None or title is None:
        return None

    issue_id = issue_id.strip()
    title = title.strip()
    if not issue_id or not title or _has_prefix(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _is_status_change_event(event: Mapping[str, Any]) -> bool:
    markers = {_normalize_words(value) for value in _marker_values(event)}
    markers.discard("")

    if markers & _DIRECT_STATUS_CHANGE_EVENTS:
        return True

    if markers & _GENERIC_UPDATE_EVENTS:
        return _status_field_was_updated(event)

    return False


def _marker_values(event: Mapping[str, Any]) -> Iterable[Any]:
    for payload in _metadata_payloads(event):
        for key in _MARKER_KEYS:
            if key in payload:
                yield payload[key]


def _status_field_was_updated(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, nested_value in value.items():
            normalized_key = _normalize_words(key)
            if normalized_key in {"updated fields", "changed fields"}:
                if _contains_status_field(nested_value):
                    return True
            if normalized_key in {"changes", "changed", "updated from", "updatedfrom"}:
                if _change_payload_mentions_status(nested_value):
                    return True
            if _status_field_was_updated(nested_value):
                return True
    elif _is_sequence(value):
        return any(_status_field_was_updated(item) for item in value)

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(_is_status_field(key) for key in value)
    if _is_sequence(value):
        return any(_is_status_field(item) for item in value)
    return _is_status_field(value)


def _change_payload_mentions_status(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(_is_status_field(key) for key in value)
    if _is_sequence(value):
        return any(_change_payload_mentions_status(item) for item in value)
    return False


def _is_status_field(value: Any) -> bool:
    normalized = _normalize_words(value)
    if normalized in _STATUS_FIELD_NAMES:
        return True
    return normalized.endswith(" status") or normalized.endswith(" state")


def _find_new_status(event: Mapping[str, Any]) -> str | None:
    for payload in _metadata_payloads(event):
        status = _first_string(payload, _EXPLICIT_NEW_STATUS_KEYS)
        if status is not None:
            return status

    status = _status_from_change_payload(event)
    if status is not None:
        return status

    for payload in _status_payloads(event):
        status = _first_string(payload, _CURRENT_STATUS_KEYS)
        if status is not None:
            return status

    return None


def _status_from_change_payload(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key, nested_value in value.items():
            normalized_key = _normalize_words(key)
            if normalized_key in {"changes", "changed"}:
                status = _status_from_change_payload(nested_value)
                if status is not None:
                    return status
            if _is_status_field(key):
                status = _extract_new_value(nested_value)
                if status is not None:
                    return status
        for nested_value in value.values():
            status = _status_from_change_payload(nested_value)
            if status is not None:
                return status
    elif _is_sequence(value):
        for item in value:
            status = _status_from_change_payload(item)
            if status is not None:
                return status

    return None


def _extract_new_value(value: Any) -> str | None:
    if isinstance(value, Mapping):
        status = _first_string(
            value,
            (
                "new",
                "newValue",
                "new_value",
                "to",
                "after",
                "name",
                "title",
                "status",
                "state",
            ),
        )
        if status is not None:
            return status
    return _string_value(value)


def _find_issue_value(event: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for payload in _issue_payloads(event):
        value = _first_string(payload, keys)
        if value is not None:
            return value
    return None


def _first_string(payload: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        if key in payload:
            value = _string_value(payload[key])
            if value is not None:
                return value
    return None


def _string_value(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None

    if isinstance(value, Mapping):
        for key in ("name", "title", "label", "status", "state", "identifier", "id"):
            if key in value:
                nested_value = _string_value(value[key])
                if nested_value is not None:
                    return nested_value

    return None


def _metadata_payloads(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    payloads = [event]
    for path in (
        ("triggerContext",),
        ("data",),
        ("data", "issue"),
        ("issue",),
    ):
        payload = _get_mapping(event, path)
        if payload is not None:
            payloads.append(payload)
    return payloads


def _status_payloads(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    payloads = []
    for path in (
        ("triggerContext",),
        ("data",),
        ("data", "issue"),
        ("issue",),
        (),
    ):
        payload = event if not path else _get_mapping(event, path)
        if payload is not None:
            payloads.append(payload)
    return payloads


def _issue_payloads(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    payloads = []
    for path in (
        ("triggerContext",),
        ("data", "issue"),
        ("issue",),
        ("data",),
        (),
    ):
        payload = event if not path else _get_mapping(event, path)
        if payload is not None:
            payloads.append(payload)
    return payloads


def _get_mapping(payload: Mapping[str, Any], path: tuple[str, ...]) -> Mapping[str, Any] | None:
    value: Any = payload
    for key in path:
        if not isinstance(value, Mapping):
            return None
        value = value.get(key)
    return value if isinstance(value, Mapping) else None


def _normalize_words(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    value = re.sub(r"[^A-Za-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip().lower()


def _has_prefix(title: str) -> bool:
    return title.lower().startswith(PREFIX.lower())


def _is_sequence(value: Any) -> bool:
    return isinstance(value, Iterable) and not isinstance(value, (str, bytes, Mapping))


def main() -> int:
    event = json.load(sys.stdin)
    result = build_issue_title_update(event)
    if result is not None:
        print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
