"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable, Mapping
from typing import Any


PREFIX = "Cursor researching"
TARGET_STATUS = "to research"

_STATUS_FIELD_NAMES = {"status", "state", "workflowstate"}
_EVENT_NAME_FIELDS = ("trigger", "action", "type", "webhookType", "event", "webhook_type")
_ISSUE_ID_FIELDS = ("issueId", "issue_id", "identifier", "key", "id")
_EXPLICIT_STATUS_FIELDS = ("newStatus", "new_status", "newState", "new_state", "newWorkflowState")
_FALLBACK_STATUS_FIELDS = ("status", "state", "workflowState", "workflow_state")


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return an issue-title update action when a Linear issue moves to To Research.

    The Cursor automation payload is usually flat under ``triggerContext``. Linear
    webhooks can also be nested under ``data`` or ``issue``, so extraction is
    intentionally tolerant while keeping the update condition narrow.
    """

    if not isinstance(event, Mapping):
        return None

    payloads = _payload_candidates(event)
    if not _is_status_change_event(payloads, event):
        return None

    status = _new_status(payloads, event)
    if _normalize_token(status) != _normalize_token(TARGET_STATUS):
        return None

    title = _string_field(payloads, ("title", "name"))
    issue_id = _string_field(payloads, _ISSUE_ID_FIELDS)
    if title is None or issue_id is None:
        return None

    title = title.strip()
    issue_id = issue_id.strip()
    if not title or not issue_id:
        return None

    if title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def _payload_candidates(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    candidates: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and value not in candidates:
            candidates.append(value)

    add(event.get("triggerContext"))
    add(event.get("issue"))

    data = event.get("data")
    if isinstance(data, Mapping):
        add(data.get("issue"))
        add(data)

    add(event)
    return candidates


def _is_status_change_event(payloads: Iterable[Mapping[str, Any]], event: Mapping[str, Any]) -> bool:
    for payload in payloads:
        for field in _EVENT_NAME_FIELDS:
            if _is_direct_status_change(payload.get(field)):
                return True

    if _is_generic_issue_update(payloads):
        return _has_status_field_update(event)

    return False


def _is_direct_status_change(value: Any) -> bool:
    normalized = _normalize_token(value)
    return any(marker in normalized for marker in ("statuschanged", "statechanged", "workflowstatechanged"))


def _is_generic_issue_update(payloads: Iterable[Mapping[str, Any]]) -> bool:
    for payload in payloads:
        for field in _EVENT_NAME_FIELDS:
            normalized = _normalize_token(payload.get(field))
            if normalized in {"update", "updated", "issueupdate", "issueupdated", "updatedissue"}:
                return True
    return False


def _has_status_field_update(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            normalized_key = _normalize_token(key)
            if normalized_key in {"updatedfields", "changedfields"}:
                if _contains_status_field(nested):
                    return True
            if normalized_key in {"changes", "change"}:
                if _changes_include_status(nested):
                    return True
            if isinstance(nested, (Mapping, list, tuple)) and _has_status_field_update(nested):
                return True
    elif isinstance(value, list | tuple):
        return any(_has_status_field_update(item) for item in value)
    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_token(value) in _STATUS_FIELD_NAMES
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if _normalize_token(key) in _STATUS_FIELD_NAMES:
                return True
            if _normalize_token(nested) in _STATUS_FIELD_NAMES:
                return True
            if isinstance(nested, (Mapping, list, tuple)) and _contains_status_field(nested):
                return True
    if isinstance(value, list | tuple):
        return any(_contains_status_field(item) for item in value)
    return False


def _changes_include_status(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(
            _normalize_token(key) in _STATUS_FIELD_NAMES or _contains_status_field(nested)
            for key, nested in value.items()
        )
    return _contains_status_field(value)


def _new_status(payloads: Iterable[Mapping[str, Any]], event: Mapping[str, Any]) -> str | None:
    status = _string_field(payloads, _EXPLICIT_STATUS_FIELDS)
    if status is not None:
        return status

    status = _status_from_changes(event)
    if status is not None:
        return status

    status = _string_field(payloads, _FALLBACK_STATUS_FIELDS)
    if status is not None:
        return status

    return _status_from_changes(event)


def _status_from_changes(value: Any) -> str | None:
    if isinstance(value, Mapping):
        if any(_normalize_token(value.get(field)) in _STATUS_FIELD_NAMES for field in ("field", "name", "key")):
            status = _status_value(value)
            if status is not None and _normalize_token(status) not in _STATUS_FIELD_NAMES:
                return status

        for key, nested in value.items():
            normalized_key = _normalize_token(key)
            if normalized_key in _STATUS_FIELD_NAMES:
                status = _status_value(nested)
                if status is not None:
                    return status
            if normalized_key in {"changes", "change", "updatedfields", "changedfields"}:
                status = _status_from_changes(nested)
                if status is not None:
                    return status
            elif isinstance(nested, (Mapping, list, tuple)):
                status = _status_from_changes(nested)
                if status is not None:
                    return status
    elif isinstance(value, list | tuple):
        for item in value:
            status = _status_from_changes(item)
            if status is not None:
                return status
    return None


def _string_field(payloads: Iterable[Mapping[str, Any]], field_names: Iterable[str]) -> str | None:
    for payload in payloads:
        for field in field_names:
            value = payload.get(field)
            extracted = _status_value(value)
            if extracted is not None:
                return extracted
    return None


def _status_value(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        for key in ("newValue", "new_value", "to", "after", "current", "value", "name", "title"):
            extracted = _status_value(value.get(key))
            if extracted is not None:
                return extracted
    return None


def _normalize_token(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    return re.sub(r"[^a-z0-9]+", "", spaced.lower())


def main() -> int:
    payload = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(payload)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
