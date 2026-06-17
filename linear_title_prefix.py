"""Build Linear issue title updates for Cursor research status changes."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping
from typing import Any


RESEARCH_STATUS = "to research"
TITLE_PREFIX = "Cursor researching"
TITLE_PREFIX_RE = re.compile(r"^\s*cursor\s+researching\b", re.IGNORECASE)
STATUS_FIELDS = {"status", "state", "workflowstate", "workflow state"}
DIRECT_STATUS_TRIGGERS = {
    "status changed",
    "status change",
    "state changed",
    "state change",
    "workflow state changed",
    "workflow state change",
}


def build_issue_title_update(event: Mapping[str, Any]) -> dict[str, str] | None:
    """Return a Linear title update action when an issue enters research status."""

    if not isinstance(event, Mapping):
        return None

    payload = _flatten_payload(event)
    if not _is_status_change_event(payload):
        return None

    status = _new_status(payload)
    if _normalize_words(status) != RESEARCH_STATUS:
        return None

    issue_id = _first_text(payload, ("issueId", "issue_id", "identifier", "key", "id"))
    title = _first_text(payload, ("title", "name"))
    if not issue_id or not title:
        return None

    if TITLE_PREFIX_RE.match(title):
        return None

    return {
        "action": "update_issue_title",
        "issueId": issue_id,
        "title": f"{TITLE_PREFIX}: {title}",
    }


def _flatten_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    """Merge useful nested Linear/Cursor payload levels into one lookup map."""

    result: dict[str, Any] = {}

    def merge(value: Any) -> None:
        if isinstance(value, Mapping):
            result.update(value)

    def nested(value: Any, *keys: str) -> Any:
        current = value
        for key in keys:
            if not isinstance(current, Mapping):
                return None
            current = current.get(key)
        return current

    merge(nested(event, "data", "issue"))
    merge(nested(event, "issue"))
    merge(nested(event, "data"))
    merge(nested(event, "triggerContext"))
    merge(event)

    # Preserve nested objects that may carry a status name after top-level merges.
    for key in ("state", "workflowState", "status"):
        for source in (
            nested(event, "data", "issue", key),
            nested(event, "issue", key),
            nested(event, "data", key),
            event.get(key),
            nested(event, "triggerContext", key),
        ):
            if isinstance(source, Mapping) and key not in result:
                result[key] = source

    return result


def _is_status_change_event(payload: Mapping[str, Any]) -> bool:
    event_names = [
        _normalize_words(payload.get(key))
        for key in ("trigger", "webhookType", "action", "type", "event", "eventType")
    ]
    event_names = [name for name in event_names if name]

    if any(name in DIRECT_STATUS_TRIGGERS for name in event_names):
        return True

    if _changed_status_field(payload):
        return True

    return False


def _changed_status_field(payload: Mapping[str, Any]) -> bool:
    for key in ("updatedFields", "changedFields", "changed_fields"):
        if _contains_status_field(payload.get(key)):
            return True

    for key in ("changes", "changed", "updatedFrom", "updated_from"):
        changes = payload.get(key)
        if isinstance(changes, Mapping) and any(
            _normalize_words(field) in STATUS_FIELDS for field in changes
        ):
            return True
        if isinstance(changes, list) and any(_change_mentions_status(change) for change in changes):
            return True

    return False


def _contains_status_field(value: Any) -> bool:
    if isinstance(value, str):
        return _normalize_words(value) in STATUS_FIELDS

    if isinstance(value, (list, tuple, set)):
        return any(_contains_status_field(item) for item in value)

    if isinstance(value, Mapping):
        return any(
            _normalize_words(key) in STATUS_FIELDS or _contains_status_field(item)
            for key, item in value.items()
        )

    return False


def _change_mentions_status(change: Any) -> bool:
    if isinstance(change, str):
        return _normalize_words(change) in STATUS_FIELDS
    if not isinstance(change, Mapping):
        return False

    for key in ("field", "fieldName", "name", "key"):
        if _normalize_words(change.get(key)) in STATUS_FIELDS:
            return True

    return any(_normalize_words(key) in STATUS_FIELDS for key in change)


def _new_status(payload: Mapping[str, Any]) -> str | None:
    direct_keys = (
        "newStatus",
        "new_status",
        "statusName",
        "status_name",
        "stateName",
        "state_name",
        "workflowStateName",
        "workflow_state_name",
    )
    value = _first_text(payload, direct_keys)
    if value:
        return value

    value = _status_from_change_metadata(payload)
    if value:
        return value

    for key in ("status", "state", "workflowState"):
        value = _status_name(payload.get(key))
        if value:
            return value

    return None


def _status_from_change_metadata(payload: Mapping[str, Any]) -> str | None:
    for key in ("changes", "changed"):
        changes = payload.get(key)
        if isinstance(changes, Mapping):
            for field, change in changes.items():
                if _normalize_words(field) in STATUS_FIELDS:
                    value = _changed_to_value(change)
                    if value:
                        return value
        elif isinstance(changes, list):
            for change in changes:
                if _change_mentions_status(change):
                    value = _changed_to_value(change)
                    if value:
                        return value

    return None


def _changed_to_value(change: Any) -> str | None:
    if isinstance(change, str):
        return _clean_text(change)

    if isinstance(change, Mapping):
        for key in ("to", "new", "newValue", "after", "value", "name"):
            value = _status_name(change.get(key))
            if value:
                return value

    return None


def _status_name(value: Any) -> str | None:
    if isinstance(value, str):
        return _clean_text(value)

    if isinstance(value, Mapping):
        return _first_text(value, ("name", "label", "title", "value"))

    return None


def _first_text(payload: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str):
            cleaned = _clean_text(value)
            if cleaned:
                return cleaned
        elif isinstance(value, (int, float)):
            return str(value)
    return None


def _clean_text(value: str) -> str | None:
    stripped = value.strip()
    return stripped or None


def _normalize_words(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^a-zA-Z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def main() -> int:
    event = json.load(sys.stdin)
    update = build_issue_title_update(event)
    if update is not None:
        print(json.dumps(update, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
