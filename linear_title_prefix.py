"""Build Linear issue-title updates for Cursor research automation events."""

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
    "workflowstate",
    "workflow_state",
}
_STATUS_CHANGE_HINTS = {
    "statuschanged",
    "status_changed",
    "status change",
    "status changed",
}
_GENERIC_UPDATE_HINTS = {
    "update",
    "updated",
    "issue update",
    "issue updated",
    "updated issue",
}


def build_issue_title_update(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Return a Linear title update action when an issue moves to To Research.

    The automation trigger payload may be a flat Cursor `triggerContext` object or a
    nested Linear webhook-style object. This function intentionally has no side
    effects so the caller can decide how to apply the returned update.
    """

    if not isinstance(event, Mapping):
        return None

    payloads = _candidate_payloads(event)
    if not _is_status_change_event(payloads):
        return None

    new_status = _find_new_status(payloads)
    if _normalize_label(new_status) != TARGET_STATUS:
        return None

    issue = _find_issue_payload(payloads)
    issue_id = _first_text(issue, ("id", "issueId", "issue_id", "identifier", "key", "uuid"))
    title = _first_text(issue, ("title", "name"))

    if not issue_id or not title:
        return None
    if title.lower().startswith(PREFIX.lower()):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{PREFIX}: {title}",
    }


def handle_issue_status_changed(event: Mapping[str, Any] | None) -> dict[str, str] | None:
    """Backward-compatible alias for callers that use an event-handler name."""

    return build_issue_title_update(event)


def _candidate_payloads(event: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    payloads: list[Mapping[str, Any]] = []

    def add(value: Any) -> None:
        if isinstance(value, Mapping) and not any(value is payload for payload in payloads):
            payloads.append(value)

    add(event)
    for key in ("triggerContext", "trigger_context", "data", "issue"):
        value = event.get(key)
        add(value)
        if isinstance(value, Mapping):
            add(value.get("triggerContext"))
            add(value.get("trigger_context"))
            add(value.get("data"))
            add(value.get("issue"))
            add(value.get("state"))
            add(value.get("workflowState"))

    return payloads


def _is_status_change_event(payloads: Iterable[Mapping[str, Any]]) -> bool:
    saw_explicit_event = False

    for payload in payloads:
        for key in ("trigger", "webhookType", "webhook_type", "action", "type"):
            event_name = _normalize_event_name(payload.get(key))
            if not event_name:
                continue
            if event_name in _STATUS_CHANGE_HINTS:
                return True
            if event_name in _GENERIC_UPDATE_HINTS:
                saw_explicit_event = True

        if _changed_status_fields(payload):
            return True

    return saw_explicit_event and any(_changed_status_fields(payload) for payload in payloads)


def _changed_status_fields(payload: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "updated_fields", "changedFields", "changed_fields"):
        if _contains_status_field(payload.get(key)):
            return True

    for key in ("changes", "updatedFrom", "updated_from"):
        value = payload.get(key)
        if isinstance(value, Mapping) and any(_is_status_field_name(field) for field in value):
            return True

    return False


def _find_new_status(payloads: Iterable[Mapping[str, Any]]) -> Any:
    status_keys = (
        "newStatus",
        "new_status",
        "toStatus",
        "to_status",
        "statusName",
        "status_name",
        "stateName",
        "state_name",
        "workflowStateName",
        "workflow_state_name",
    )
    fallback: Any = None

    for payload in payloads:
        for key in status_keys:
            if payload.get(key) is not None:
                return payload[key]

        for key in ("status", "state", "workflowState", "workflow_state"):
            value = payload.get(key)
            if isinstance(value, Mapping):
                for nested_key in ("name", "title", "key", "id"):
                    if value.get(nested_key) is not None:
                        fallback = value[nested_key]
                        break
            elif value is not None and key != "workflow_state":
                fallback = value

        for key in ("changes",):
            changed_value = _status_value_from_changes(payload.get(key))
            if changed_value is not None:
                return changed_value

    return fallback


def _status_value_from_changes(value: Any) -> Any:
    if not isinstance(value, Mapping):
        return None

    for field_name, field_change in value.items():
        if not _is_status_field_name(str(field_name)):
            continue
        if isinstance(field_change, Mapping):
            for key in ("newValue", "new_value", "to", "after", "value", "name"):
                if field_change.get(key) is not None:
                    return field_change[key]
        elif field_change is not None:
            return field_change

    return None


def _find_issue_payload(payloads: Iterable[Mapping[str, Any]]) -> Mapping[str, Any]:
    best: Mapping[str, Any] | None = None

    for payload in payloads:
        if isinstance(payload.get("issue"), Mapping):
            nested_issue = payload["issue"]
            if _has_issue_identity(nested_issue):
                return nested_issue

        if _has_issue_identity(payload):
            best = payload

    return best or {}


def _has_issue_identity(payload: Mapping[str, Any]) -> bool:
    return bool(
        _first_text(payload, ("id", "issueId", "issue_id", "identifier", "key", "uuid"))
        and _first_text(payload, ("title", "name"))
    )


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _is_status_field_name(value)
    if isinstance(value, Mapping):
        return any(_is_status_field_name(str(key)) for key in value)
    if isinstance(value, Iterable):
        return any(_contains_status_field(item) for item in value)
    return False


def _is_status_field_name(value: str) -> bool:
    normalized = _normalize_field_name(value)
    return normalized in _STATUS_FIELD_NAMES


def _first_text(payload: Mapping[str, Any], keys: Iterable[str]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str):
            stripped = value.strip()
            if stripped:
                return stripped
    return None


def _normalize_field_name(value: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "", value.replace("-", "_").lower())


def _normalize_event_name(value: Any) -> str:
    return _normalize_label(value)


def _normalize_label(value: Any) -> str:
    if isinstance(value, Mapping):
        for key in ("name", "title", "key", "id"):
            if value.get(key) is not None:
                return _normalize_label(value[key])
        return ""
    if value is None:
        return ""

    text = str(value).strip()
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def main() -> int:
    event = json.load(sys.stdin)
    print(json.dumps(build_issue_title_update(event), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
